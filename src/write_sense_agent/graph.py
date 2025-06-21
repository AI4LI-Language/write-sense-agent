"""
Main graph definition for WriteSense Agent.

This module defines the primary agent graph that can be deployed 
using langgraph-cli for production hosting.
"""

import os
import glob
import inspect
from pathlib import Path
from typing import Any, Dict, Optional

from write_sense_agent.core.config import AgentConfig, TransportType
from write_sense_agent.core.mcp_agent import MCPAgent
from write_sense_agent.core.orchestrator import OrchestratorAgent


def discover_mcp_servers(mcp_servers_dir: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Dynamically discover MCP servers from the mcp_servers directory.
    
    Args:
        mcp_servers_dir: Path to the MCP servers directory (defaults to ./mcp_servers)
        
    Returns:
        Dictionary of server configurations keyed by server name
    """
    if mcp_servers_dir is None:
        # Get the project root directory
        current_file = Path(__file__)
        # From src/write_sense_agent/graph.py, go up to write-sense-agent/, then to mcp_servers/
        project_root = current_file.parent.parent.parent  # Go up to write-sense-agent/
        mcp_servers_dir = project_root / "mcp_servers"
    else:
        mcp_servers_dir = Path(mcp_servers_dir)
    
    discovered_servers = {}
    
    print(f"Looking for MCP servers in: {mcp_servers_dir}")
    
    if not mcp_servers_dir.exists():
        print(f"Warning: MCP servers directory not found: {mcp_servers_dir}")
        return discovered_servers
    
    # Find all Python files in the mcp_servers directory
    server_files = list(mcp_servers_dir.glob("*_server.py"))
    
    for server_file in server_files:
        try:
            # Extract server name from filename (remove _server.py suffix)
            server_name = server_file.stem.replace("_server", "")
            
            # Check if the file has a shebang and appears to be executable
            with open(server_file, 'r') as f:
                first_line = f.readline().strip()
                
            # Determine if it's a FastMCP server or regular stdio server
            server_config = {
                "name": server_name,
                "transport": TransportType.STDIO,
                "command": "python",
                "args": [str(server_file)],
                "env": {}
            }
            
            # Add any environment variables that might be needed
            # You can extend this logic based on your server requirements
            if "search" in server_name.lower() or "web" in server_name.lower():
                # For search servers, might need API keys
                server_config["env"]["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
            
            discovered_servers[server_name] = server_config
            print(f"Discovered MCP server: {server_name} -> {server_file}")
            
        except Exception as e:
            print(f"Warning: Could not process MCP server file {server_file}: {e}")
            continue
    
    return discovered_servers


def get_agent_config() -> AgentConfig:
    """
    Get or create the agent configuration with dynamic MCP server discovery.
    
    Returns:
        Configured AgentConfig instance
    """
    # Initialize configuration from environment
    config = AgentConfig.from_env()
    
    # Dynamically discover and add MCP servers
    if not config.mcp_servers:
        discovered_servers = discover_mcp_servers()
        
        for server_name, server_config in discovered_servers.items():
            config.add_mcp_server(
                name=server_config["name"],
                transport=server_config["transport"],
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env", {})
            )
            print(f"Added MCP server: {server_name}")

        if not discovered_servers:
            print("No MCP servers discovered. The agent will run without external tools.")
    
    return config


async def create_agent_system() -> OrchestratorAgent:
    """
    Create and initialize the complete agent system.
    
    Returns:
        Initialized orchestrator agent
    """
    # Get configuration with dynamic server discovery
    config = get_agent_config()
    
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