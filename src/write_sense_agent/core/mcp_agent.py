"""MCP Agent module for handling tools from individual MCP servers."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from write_sense_agent.core.config import AgentConfig, MCPServerConfig, TransportType


logger = logging.getLogger(__name__)


class MCPAgent:
    """
    Agent that handles tools from one or more MCP servers.
    
    This agent connects to MCP servers, loads their tools, and creates
    a ReAct agent to interact with those tools.
    """
    
    def __init__(
        self,
        name: str,
        config: AgentConfig,
        server_configs: Dict[str, MCPServerConfig],
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize the MCP Agent.
        
        Args:
            name: Agent name
            config: Agent configuration
            server_configs: MCP server configurations
            system_prompt: Custom system prompt for this agent
        """
        self.name = name
        self.config = config
        self.server_configs = server_configs
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # Agent components
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List[BaseTool] = []
        self.agent = None
        self.checkpointer = MemorySaver() if config.orchestrator.enable_memory else None
        
        # Create LLM
        self.llm = self._create_llm()
        
        logger.info(f"Initialized MCP Agent '{name}' with {len(server_configs)} servers")
    
    def _default_system_prompt(self) -> str:
        """Generate default system prompt for this agent."""
        server_names = list(self.server_configs.keys())
        return (
            f"You are a specialized agent named '{self.name}' that can access tools from "
            f"the following MCP servers: {', '.join(server_names)}. "
            f"Use the available tools to help answer user questions effectively. "
            f"Provide clear, accurate responses based on the tool results."
        )
    
    def _create_llm(self) -> Any:
        """Create the language model based on configuration."""
        llm_config = self.config.mcp_agents_llm  # Use MCP agents-specific LLM config
        
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
    
    async def initialize(self) -> None:
        """Initialize the agent by connecting to MCP servers and loading tools."""
        if len(self.server_configs) == 1:
            # Single server - use direct connection
            await self._initialize_single_server()
        else:
            # Multiple servers - use MultiServerMCPClient
            await self._initialize_multi_server()
        
        # Create the ReAct agent
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=self.system_prompt,
            checkpointer=self.checkpointer,
        )
        
        logger.info(f"Agent '{self.name}' initialized with {len(self.tools)} tools")
    
    async def _initialize_single_server(self) -> None:
        """Initialize agent with a single MCP server."""
        server_name, server_config = next(iter(self.server_configs.items()))
        
        if server_config.transport == TransportType.STDIO:
            await self._load_stdio_tools(server_config)
        elif server_config.transport in (TransportType.SSE, TransportType.STREAMABLE_HTTP):
            await self._load_http_tools(server_config)
        else:
            raise ValueError(f"Unsupported transport type: {server_config.transport}")
    
    async def _initialize_multi_server(self) -> None:
        """Initialize agent with multiple MCP servers using MultiServerMCPClient."""
        # Convert server configs to MultiServerMCPClient format
        client_config = {}
        for name, config in self.server_configs.items():
            if config.transport == TransportType.STDIO:
                client_config[name] = {
                    "command": config.command,
                    "args": config.args,
                    "transport": "stdio",
                }
                if config.env:
                    client_config[name]["env"] = config.env
            elif config.transport == TransportType.SSE:
                client_config[name] = {
                    "url": config.url,
                    "transport": "sse",
                }
            elif config.transport == TransportType.STREAMABLE_HTTP:
                client_config[name] = {
                    "url": config.url,
                    "transport": "streamable_http",
                }
        
        # Initialize client
        self.client = MultiServerMCPClient(client_config)
        await self.client.__aenter__()
        
        # Load tools
        self.tools = self.client.get_tools()
    
    async def _load_stdio_tools(self, server_config: MCPServerConfig) -> None:
        """Load tools from a stdio MCP server."""
        server_params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env or None,
        )
        
        # Note: For production use, you might want to keep the connection alive
        # This is a simplified version for demonstration
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.tools = await load_mcp_tools(session)
    
    async def _load_http_tools(self, server_config: MCPServerConfig) -> None:
        """Load tools from an HTTP/SSE MCP server."""
        # Note: This is a simplified implementation
        # In production, you might want to use a more robust HTTP client
        async with streamablehttp_client(server_config.url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.tools = await load_mcp_tools(session)
    
    async def invoke(
        self,
        messages: Sequence[BaseMessage],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke the agent with a sequence of messages.
        
        Args:
            messages: Input messages
            config: Optional configuration for the invocation
            
        Returns:
            Agent response
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Use default config if none provided
        if config is None:
            config = self.config.get_langgraph_config()
        
        return await self.agent.ainvoke({"messages": messages}, config=config)
    
    async def stream(
        self,
        messages: Sequence[BaseMessage],
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Stream the agent's response.
        
        Args:
            messages: Input messages
            config: Optional configuration for the invocation
            
        Returns:
            Async generator of response chunks
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Use default config if none provided
        if config is None:
            config = self.config.get_langgraph_config()
        
        async for chunk in self.agent.astream({"messages": messages}, config=config):
            yield chunk
    
    def get_tools(self) -> List[BaseTool]:
        """Get the list of available tools."""
        return self.tools
    
    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Get descriptions of available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args": str(tool.args) if hasattr(tool, "args") else "N/A",
            }
            for tool in self.tools
        ]
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up MCP client: {e}")
        
        logger.info(f"Cleaned up MCP Agent '{self.name}'")
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"MCPAgent(name='{self.name}', "
            f"servers={list(self.server_configs.keys())}, "
            f"tools={len(self.tools)})"
        ) 