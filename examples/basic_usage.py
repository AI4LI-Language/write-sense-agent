#!/usr/bin/env python3
"""
Basic usage example for WriteSense Agent.

This example demonstrates how to set up and use the agent system
with multiple MCP servers.
"""

import asyncio
import os
from pathlib import Path

from write_sense_agent.core.config import AgentConfig, TransportType
from write_sense_agent.core.mcp_agent import MCPAgent
from write_sense_agent.core.orchestrator import OrchestratorAgent


async def main():
    """Main example function."""
    print("🚀 WriteSense Agent - Basic Usage Example")
    print("=" * 50)
    
    # Create configuration from environment
    config = AgentConfig.from_env()
    
    # Add MCP servers
    print("📡 Configuring MCP servers...")
    
    # Document server (stdio)
    config.add_mcp_server(
        name="document_server",
        transport=TransportType.STDIO,
        command="python",
        args=[str(Path(__file__).parent.parent / "mcp_servers" / "document_server.py")],
    )
    
    # Web server (stdio) - you can also run it as SSE
    config.add_mcp_server(
        name="web_server",
        transport=TransportType.STDIO,
        command="python",
        args=[str(Path(__file__).parent.parent / "mcp_servers" / "web_server.py")],
    )
    
    # Create orchestrator
    print("🎯 Creating orchestrator agent...")
    orchestrator = OrchestratorAgent(config)
    
    # Create specialized agents
    print("🤖 Creating specialized agents...")
    
    # Document agent
    doc_agent = MCPAgent(
        name="document_agent",
        config=config,
        server_configs={"document_server": config.mcp_servers["document_server"]},
        system_prompt="You are a document specialist. Use your tools to search, retrieve, and analyze documents effectively."
    )
    orchestrator.add_mcp_agent(doc_agent)
    
    # Web agent
    web_agent = MCPAgent(
        name="web_agent", 
        config=config,
        server_configs={"web_server": config.mcp_servers["web_server"]},
        system_prompt="You are a web specialist. Use your tools to fetch web content, search the web, and analyze websites."
    )
    orchestrator.add_mcp_agent(web_agent)
    
    # Initialize the system
    print("⚡ Initializing agent system...")
    await orchestrator.initialize()
    
    # Show capabilities
    print("\n🛠️  Agent Capabilities:")
    capabilities = orchestrator.get_agent_capabilities()
    for agent_name, caps in capabilities.items():
        print(f"  • {agent_name}: {caps['tool_count']} tools")
        for tool in caps['tools'][:3]:  # Show first 3 tools
            print(f"    - {tool['name']}: {tool['description']}")
        if caps['tool_count'] > 3:
            print(f"    ... and {caps['tool_count'] - 3} more tools")
    
    # Example queries
    queries = [
        "Search for documents about AI and machine learning",
        "What documents do you have available?",
        "Check if the website https://example.com is accessible",
        "What can you help me with?",
    ]
    
    print(f"\n💬 Running example queries...")
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: {query} ---")
        
        try:
            # Stream the response
            response_parts = []
            config = {"configurable": {"thread_id": f"test_thread_{i}"}}
            async for chunk in orchestrator.stream(query, config=config):
                for node_name, data in chunk.items():
                    if "messages" in data and data["messages"]:
                        message = data["messages"][-1]
                        if hasattr(message, "content") and message.content:
                            # Only print the final response, not intermediate steps
                            if node_name == "agent":
                                response_parts.append(message.content)
            
            # Print the final response
            if response_parts:
                print(f"🤖 Response: {response_parts[-1]}")
            else:
                print("🤖 No response received")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
        
        # Add a small delay between queries
        await asyncio.sleep(1)
    
    # Cleanup
    print(f"\n🧹 Cleaning up...")
    await orchestrator.cleanup()
    print("✅ Example completed successfully!")


if __name__ == "__main__":
    # Set up basic environment if not already configured
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: No API keys found in environment.")
        print("Please set ANTHROPIC_API_KEY or OPENAI_API_KEY to run this example.")
        print("You can also create a .env file with your configuration.")
        exit(1)
    
    # Run the example
    asyncio.run(main()) 