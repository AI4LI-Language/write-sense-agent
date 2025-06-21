#!/usr/bin/env python3
"""
Tavily Search MCP Server for WriteSense Agent.

This server provides tools for advanced web search using Tavily Search API.
It demonstrates how to create a standard MCP server for AI-powered search tasks.
Tavily is specifically designed for AI agents and provides real-time, accurate search results.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    TextContent,
    Tool,
)
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import tavily-python, provide helpful error if not installed
try:
    from tavily import TavilyClient
except ImportError:
    logger.error("tavily-python is not installed. Install it with: pip install tavily-python")
    TavilyClient = None

# Initialize Tavily client
def get_tavily_client() -> Optional[TavilyClient]:
    """Initialize and return Tavily client with API key from environment."""
    if TavilyClient is None:
        return None
        
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        logger.warning("TAVILY_API_KEY environment variable not set")
        return None
    return TavilyClient(api_key=api_key)

# Create the MCP server
server = Server("tavily-search")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="tavily_search",
            description="Search the web using Tavily Search API for comprehensive and accurate results. Best for current events, factual information, and real-time data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (default: 5, max: 20)",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5
                    },
                    "search_depth": {
                        "type": "string",
                        "description": "Search depth: 'basic' for quick results, 'advanced' for comprehensive search",
                        "enum": ["basic", "advanced"],
                        "default": "basic"
                    },
                    "include_answer": {
                        "type": "boolean",
                        "description": "Include a direct answer to the query if available",
                        "default": True
                    },
                    "include_raw_content": {
                        "type": "boolean", 
                        "description": "Include raw HTML content of search results",
                        "default": False
                    },
                    "include_images": {
                        "type": "boolean",
                        "description": "Include related images in search results",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="tavily_quick_answer",
            description="Get a quick answer to a question using Tavily's search and answer API. Best for direct questions that need immediate answers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to get an answer for"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="tavily_health_check",
            description="Check if Tavily API is accessible and working correctly.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "tavily_search":
        return await handle_tavily_search(arguments)
    elif name == "tavily_quick_answer":
        return await handle_tavily_quick_answer(arguments)
    elif name == "tavily_health_check":
        return await handle_tavily_health_check(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def handle_tavily_search(arguments: dict) -> list[TextContent]:
    """Handle tavily search requests."""
    try:
        client = get_tavily_client()
        if not client:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Tavily client not available. Check API key and tavily-python installation.",
                    "status": "error"
                })
            )]
        
        query = arguments.get("query", "")
        if not query or not query.strip():
            return [TextContent(
                type="text", 
                text=json.dumps({"error": "Query cannot be empty"})
            )]
        
        max_results = min(max(arguments.get("max_results", 5), 1), 20)
        search_depth = arguments.get("search_depth", "basic")
        include_answer = arguments.get("include_answer", True)
        include_raw_content = arguments.get("include_raw_content", False)
        include_images = arguments.get("include_images", False)
        
        if search_depth not in ["basic", "advanced"]:
            search_depth = "basic"
        
        # Make the search request
        response = client.search(
            query=query.strip(),
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images
        )
        
        # Format result
        result = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "timestamp": datetime.utcnow().isoformat(),
            "results_count": len(response.get("results", [])),
            "results": response.get("results", []),
        }
        
        if include_answer and response.get("answer"):
            result["answer"] = response["answer"]
        
        if include_images and response.get("images"):
            result["images"] = response["images"]
        
        if response.get("follow_up_questions"):
            result["follow_up_questions"] = response["follow_up_questions"]
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in tavily_search: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Search failed: {str(e)}",
                "query": arguments.get("query", ""),
                "timestamp": datetime.utcnow().isoformat()
            })
        )]

async def handle_tavily_quick_answer(arguments: dict) -> list[TextContent]:
    """Handle quick answer requests."""
    try:
        client = get_tavily_client()
        if not client:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Tavily client not available. Check API key and tavily-python installation.",
                    "status": "error"
                })
            )]
        
        question = arguments.get("question", "")
        if not question or not question.strip():
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Question cannot be empty"})
            )]
        
        # Use qna_search for direct answers
        response = client.qna_search(query=question.strip())
        
        result = {
            "question": question,
            "answer": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in tavily_quick_answer: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Quick answer failed: {str(e)}",
                "question": arguments.get("question", ""),
                "timestamp": datetime.utcnow().isoformat()
            })
        )]

async def handle_tavily_health_check(arguments: dict) -> list[TextContent]:
    """Handle health check requests."""
    try:
        client = get_tavily_client()
        if not client:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "error",
                    "api_accessible": False,
                    "error": "Tavily client not available. Check API key and tavily-python installation.",
                    "timestamp": datetime.utcnow().isoformat()
                })
            )]
        
        # Perform a simple test search
        response = client.search(
            query="test",
            max_results=1,
            search_depth="basic",
            include_answer=False
        )
        
        result = {
            "status": "healthy",
            "api_accessible": True,
            "timestamp": datetime.utcnow().isoformat(),
            "test_results_count": len(response.get("results", []))
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "api_accessible": False,
                "error": f"API error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
        )]

async def main():
    # Initialize the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tavily-search",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    # Check if required environment variables are set
    if not os.environ.get("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY environment variable not set")
        logger.info("The server will still start but Tavily functionality will be limited")
    
    # Run the MCP server
    asyncio.run(main())
