"""Orchestrator agent for coordinating multiple MCP agents."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from write_sense_agent.core.config import AgentConfig
from write_sense_agent.core.mcp_agent import MCPAgent


logger = logging.getLogger(__name__)


class OrchestratorState(MessagesState):
    """Extended state for the orchestrator with agent tracking."""
    
    # Track which agents have been consulted
    consulted_agents: List[str] = []
    
    # Track the current step in orchestration
    orchestration_step: int = 0
    
    # Store intermediate results
    agent_results: Dict[str, Any] = {}


class OrchestratorAgent:
    """
    Orchestrator agent that coordinates multiple specialized MCP agents.
    
    This agent analyzes user requests and delegates them to appropriate
    MCP agents based on their capabilities, then synthesizes the results.
    """
    
    def __init__(self, config: AgentConfig) -> None:
        """
        Initialize the Orchestrator Agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.mcp_agents: Dict[str, MCPAgent] = {}
        self.llm = self._create_llm()
        self.checkpointer = MemorySaver() if config.orchestrator.enable_memory else None
        
        # Create orchestrator tools for agent delegation
        self.orchestrator_tools = []
        
        # Main orchestrator agent
        self.agent = None
        
        logger.info("Initialized Orchestrator Agent")
    
    def _create_llm(self) -> Any:
        """Create the language model based on configuration."""
        llm_config = self.config.orchestrator_llm  # Use orchestrator-specific LLM config
        
        if llm_config.provider.value == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                timeout=llm_config.timeout,
                api_key=llm_config.api_key,
            )
        elif llm_config.provider.value == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                timeout=llm_config.timeout,
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")
    
    def add_mcp_agent(self, agent: MCPAgent) -> None:
        """
        Add an MCP agent to the orchestrator.
        
        Args:
            agent: MCP agent to add
        """
        self.mcp_agents[agent.name] = agent
        
        # Create delegation tool for this agent
        self._create_delegation_tool(agent)
        
        logger.info(f"Added MCP agent '{agent.name}' to orchestrator")
    
    def _create_delegation_tool(self, agent: MCPAgent) -> None:
        """Create a delegation tool for an MCP agent."""
        agent_name = agent.name
        agent_obj = agent
        
        # Get tool descriptions for better delegation
        tool_descriptions = agent.get_tool_descriptions()
        tools_summary = ", ".join([t["name"] for t in tool_descriptions]) if tool_descriptions else "various tools"
        
        # Create the delegation function with proper naming
        @tool(f"delegate_to_{agent_name}")
        async def delegate_to_agent_func(query: str) -> str:
            """
            Delegate a query to a specialized MCP agent for task execution.
            
            Args:
                query: The question or task to delegate
                
            Returns:
                The agent's response
            """
            try:
                # Create message
                messages = [HumanMessage(content=query)]
                
                # Invoke agent asynchronously
                result = await agent_obj.invoke(messages)
                
                # Extract the response
                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        return last_message.content
                
                return "Agent completed the task but provided no response."
                
            except Exception as e:
                logger.error(f"Error delegating to agent {agent_name}: {e}")
                return f"Error occurred while consulting {agent_name}: {str(e)}"
        
        # Update the description after creation
        delegate_to_agent_func.description = (
            f"Delegate a query to the {agent_name} specialized MCP agent. "
            f"This agent has access to: {tools_summary}. "
            f"Use this when the user's request involves {agent_name.replace('_', ' ')} related tasks."
        )
        
        self.orchestrator_tools.append(delegate_to_agent_func)
    
    def _create_additional_tools(self) -> List[Any]:
        """Create additional tools for the orchestrator."""
        additional_tools = []
        
        # Add web search capability if available
        try:
            import os
            # Get the API key from environment variables
            tavily_api_key = os.environ.get("TAVILY_API_KEY")
            if not tavily_api_key:
                logger.warning("TAVILY_API_KEY environment variable not set. Skipping Tavily search tool.")
                return additional_tools
            
            # Use the new TavilySearch from langchain-tavily
            tavily = TavilySearch(
                max_results=3,
                search_depth="advanced",
                include_answer=True,
                # include_raw_content parameter is not available in TavilySearch from langchain-tavily
            )
            additional_tools.append(tavily)
            logger.info("Added Tavily search tool to orchestrator")
        except Exception as e:
            logger.warning(f"Could not initialize Tavily search: {e}")
        
        return additional_tools
    
    async def initialize(self) -> None:
        """Initialize the orchestrator agent."""
        # Initialize all MCP agents
        for agent in self.mcp_agents.values():
            await agent.initialize()
        
        # Combine all tools
        all_tools = self.orchestrator_tools + self._create_additional_tools()
        
        # Generate dynamic system prompt based on actual registered agents
        dynamic_prompt = self._generate_dynamic_system_prompt()
        
        # Create the main orchestrator agent
        self.agent = create_react_agent(
            self.llm,
            all_tools,
            prompt=dynamic_prompt,  # Use dynamic prompt instead of config prompt
            checkpointer=self.checkpointer,
        )
        
        logger.info(
            f"Orchestrator initialized with {len(self.mcp_agents)} MCP agents "
            f"and {len(all_tools)} total tools"
        )
    
    async def invoke(
        self,
        messages: Union[str, Sequence[BaseMessage]],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke the orchestrator with a query.
        
        Args:
            messages: Input message(s)
            config: Optional configuration
            
        Returns:
            Response from the orchestrator
        """
        if not self.agent:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        # Convert string to message if needed
        if isinstance(messages, str):
            messages = [HumanMessage(content=messages)]
        
        # Use default config if none provided
        if config is None:
            config = self.config.get_langgraph_config()
        
        return await self.agent.ainvoke({"messages": messages}, config=config)
    
    async def stream(
        self,
        messages: Union[str, Sequence[BaseMessage]],
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Stream the orchestrator's response.
        
        Args:
            messages: Input message(s)
            config: Optional configuration
            
        Returns:
            Async generator of response chunks
        """
        if not self.agent:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        # Convert string to message if needed
        if isinstance(messages, str):
            messages = [HumanMessage(content=messages)]
        
        # Use default config if none provided
        if config is None:
            config = self.config.get_langgraph_config()
        
        async for chunk in self.agent.astream({"messages": messages}, config=config):
            yield chunk
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all registered agents."""
        capabilities = {}
        
        for name, agent in self.mcp_agents.items():
            capabilities[name] = {
                "servers": list(agent.server_configs.keys()),
                "tools": agent.get_tool_descriptions(),
                "tool_count": len(agent.tools),
            }
        
        return capabilities
    
    def get_orchestrator_tools(self) -> List[str]:
        """Get list of orchestrator tool names."""
        return [tool.name for tool in self.orchestrator_tools]
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Clean up MCP agents
        for agent in self.mcp_agents.values():
            await agent.cleanup()
        
        logger.info("Orchestrator cleanup completed")
    
    def __repr__(self) -> str:
        """String representation of the orchestrator."""
        return (
            f"OrchestratorAgent("
            f"agents={list(self.mcp_agents.keys())}, "
            f"tools={len(self.orchestrator_tools)}"
            f")"
        )

    def _generate_dynamic_delegation_guidelines(self) -> str:
        """Generate delegation guidelines based on registered MCP agents."""
        if not self.mcp_agents:
            return "No specialized agents are currently available."
        
        guidelines = []
        for agent_name, agent in self.mcp_agents.items():
            tool_descriptions = agent.get_tool_descriptions()
            if tool_descriptions:
                tool_names = [t["name"] for t in tool_descriptions]
                tool_summaries = [t.get("description", t["name"]) for t in tool_descriptions]
                
                # Create intelligent guidelines based on tool names and descriptions
                capabilities = []
                for tool_desc in tool_descriptions[:3]:  # Show first 3 tools
                    name = tool_desc["name"]
                    desc = tool_desc.get("description", "")
                    if desc:
                        capabilities.append(f"{name} ({desc[:50]}{'...' if len(desc) > 50 else ''})")
                    else:
                        capabilities.append(name)
                
                capabilities_text = ", ".join(capabilities)
                if len(tool_descriptions) > 3:
                    capabilities_text += f" and {len(tool_descriptions) - 3} more tools"
                
                guideline = f"- For tasks involving {capabilities_text}, use delegate_to_{agent_name}"
                guidelines.append(guideline)
            else:
                guidelines.append(f"- For general tasks that may fit {agent_name.replace('_', ' ')} domain, use delegate_to_{agent_name}")
        
        return "\n".join(guidelines)

    def _generate_dynamic_system_prompt(self) -> str:
        """Generate a complete system prompt with dynamic delegation guidelines."""
        # Start with the configured system prompt that includes format requirements
        base_prompt = self.config.orchestrator.system_prompt
        
        # Add dynamic delegation guidelines
        delegation_guidelines = self._generate_dynamic_delegation_guidelines()
        dynamic_section = f"\n\nAVAILABLE DELEGATION OPTIONS:\n{delegation_guidelines}\n\n"
        
        # Additional guidance for demonstration
        demonstration_guidance = (
            "When a user asks about your capabilities or what you can do, ALWAYS demonstrate by using "
            "the appropriate delegation tools to show your specialized agents in action. Don't just describe "
            "what you can do - actually delegate to the relevant agents to prove your capabilities.\n\n"
            "Remember: You MUST maintain the exact Action/Content format specified above, even when delegating to sub-agents."
        )
        
        full_prompt = base_prompt + dynamic_section + demonstration_guidance
        
        # Log the generated prompt for debugging
        logger.info("Generated dynamic system prompt with delegation guidelines:")
        logger.info(f"Registered agents: {list(self.mcp_agents.keys())}")
        logger.info("Dynamic delegation section:")
        logger.info(delegation_guidelines)
        
        return full_prompt 