"""
Main graph definition for WriteSense Agent.

This module defines the primary agent graph that can be deployed 
using langgraph-cli for production hosting.
"""

import os
from typing import Any, Dict, Optional

from write_sense_agent.core.config import AgentConfig, TransportType
from write_sense_agent.core.mcp_agent import MCPAgent
from write_sense_agent.core.orchestrator import OrchestratorAgent


# Initialize configuration from environment
config = AgentConfig.from_env()

# Add example MCP servers (customize these for your use case)
if not config.mcp_servers:
    # Example: Document retrieval server (stdio)
    config.add_mcp_server(
        name="document_retriever",
        transport=TransportType.STDIO,
        command="python",
        args=["./mcp_servers/document_server.py"],
    )
    
    # Example: Web tools server (SSE)
    # Uncomment and modify if you have an SSE server
    # config.add_mcp_server(
    #     name="web_tools",
    #     transport=TransportType.SSE,
    #     url="http://localhost:8000/sse",
    # )


async def create_agent_system() -> OrchestratorAgent:
    """
    Create and initialize the complete agent system.
    
    Returns:
        Initialized orchestrator agent
    """
    # Create orchestrator
    orchestrator = OrchestratorAgent(config)
    
    # Create one MCP agent per MCP server (no grouping)
    for server_name, server_config in config.mcp_servers.items():
        # Create agent name based on server name
        agent_name = f"{server_name}_agent"
        
        # Create MCP agent for this single server
        agent = MCPAgent(
            name=agent_name,
            config=config,
            server_configs={server_name: server_config},  # Single server per agent
        )
        orchestrator.add_mcp_agent(agent)
    
    # Initialize the orchestrator (this will initialize all sub-agents)
    await orchestrator.initialize()
    
    return orchestrator


# Create the main graph for langgraph-cli deployment
# This is the entry point that langgraph-cli will use
async def create_graph():
    """
    Create the main agent graph for deployment.
    
    This function is called by langgraph-cli to create the deployable graph.
    """
    orchestrator = await create_agent_system()
    return orchestrator.agent


# For direct execution and testing
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage
    
    async def main():
        """Main function for testing the agent system."""
        print("Initializing WriteSense Agent system...")
        
        # Create and initialize the agent system
        orchestrator = await create_agent_system()
        
        print(f"Agent system initialized with capabilities:")
        capabilities = orchestrator.get_agent_capabilities()
        for agent_name, caps in capabilities.items():
            print(f"  - {agent_name}: {caps['tool_count']} tools from {caps['servers']}")
        
        # Test query
        test_query = "Hello! Can you tell me what capabilities you have?"
        print(f"\nTesting with query: {test_query}")
        
        try:
            # Stream the response
            async for chunk in orchestrator.stream(test_query):
                for node_name, data in chunk.items():
                    if "messages" in data and data["messages"]:
                        message = data["messages"][-1]
                        if hasattr(message, "content"):
                            print(f"[{node_name}] {message.content}")
        
        except Exception as e:
            print(f"Error during execution: {e}")
        
        finally:
            # Clean up
            await orchestrator.cleanup()
            print("\nAgent system cleaned up.")
    
    # Run the test
    asyncio.run(main()) 