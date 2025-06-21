# MCP Servers

This directory contains MCP (Model Context Protocol) servers that are automatically discovered and loaded by the WriteSense Agent system.

## How It Works

The agent system automatically discovers MCP servers in this directory using a simple naming convention:

- Any Python file ending with `_server.py` will be discovered and loaded
- The server name is extracted from the filename (e.g., `search_web_server.py` becomes `search_web`)
- All discovered servers are configured to use STDIO transport by default

## Available Servers

### search_web_server.py
A Tavily-powered web search server that provides:
- `tavily_search`: Advanced web search with configurable parameters
- `tavily_news_search`: Recent news article search
- `tavily_academic_search`: Academic and research content search
- `tavily_image_search`: Image search functionality  
- `tavily_quick_answer`: Quick answer to queries
- `tavily_health_check`: Server health monitoring

**Requirements:**
- `tavily-python` package: `pip install tavily-python`
- `TAVILY_API_KEY` environment variable

## Adding New MCP Servers

To add a new MCP server:

1. **Create your server file** with the naming pattern `your_server_name_server.py`
2. **Implement your MCP server** using FastMCP or standard MCP protocols
3. **Add necessary dependencies** to your virtual environment
4. **Set environment variables** if your server requires API keys or configuration

### Example Server Structure

```python
#!/usr/bin/env python3
"""
Example MCP Server for WriteSense Agent.
"""

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Example Server")

@mcp.tool()
def example_tool(message: str) -> str:
    """Example tool that echoes a message."""
    return f"Echo: {message}"

if __name__ == "__main__":
    mcp.run()
```

### Environment Variables

The discovery system automatically sets up environment variables based on server names:
- Search/web servers get `TAVILY_API_KEY`
- You can extend the logic in `graph.py` for other server types

### Supported Transport Types

Currently, all discovered servers use STDIO transport. If you need other transport types (SSE, HTTP), you can:
1. Manually configure them in your environment
2. Extend the discovery logic in `src/write_sense_agent/graph.py`

## Troubleshooting

### Server Not Discovered
- Ensure your file ends with `_server.py`
- Check that the file is in this directory
- Verify the file is valid Python and has no syntax errors

### Runtime Errors
- Check that all required dependencies are installed
- Verify environment variables are set correctly
- Look at the agent logs for specific error messages

### Testing Your Server
You can test individual servers directly:
```bash
python your_server_name_server.py
``` 