#!/usr/bin/env python3
"""
Example MCP server for web operations.

This server provides tools for web search, URL fetching, and web scraping.
It demonstrates how to create a FastMCP server for web-related tasks.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Web Operations Server")


@mcp.tool()
def fetch_url(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch content from a URL.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        Dictionary containing the response data
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"error": "Invalid URL format"}
        
        # Make request
        headers = {
            "User-Agent": "WriteSense-Agent/1.0 (MCP Web Server)"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        return {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(response.content),
            "content": response.text[:5000],  # Limit content to first 5000 chars
            "headers": dict(response.headers),
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.tool()
def extract_links(url: str, base_url: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract all links from a webpage.
    
    Args:
        url: The URL to extract links from
        base_url: Base URL for resolving relative links (defaults to the page URL)
        
    Returns:
        List of dictionaries containing link information
    """
    try:
        # Fetch the page
        result = fetch_url(url)
        if "error" in result:
            return [{"error": result["error"]}]
        
        content = result["content"]
        base_url = base_url or url
        
        # Simple regex to find links (in production, use proper HTML parser)
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
        matches = re.findall(link_pattern, content, re.IGNORECASE)
        
        links = []
        for href, text in matches:
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            links.append({
                "url": absolute_url,
                "text": text.strip(),
                "original_href": href,
            })
        
        return links[:50]  # Limit to first 50 links
        
    except Exception as e:
        return [{"error": f"Failed to extract links: {str(e)}"}]


@mcp.tool()
def search_web(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using a simple search API.
    
    Note: This is a mock implementation. In production, you would integrate
    with a real search API like Google Custom Search, Bing, or DuckDuckGo.
    
    Args:
        query: Search query
        num_results: Number of results to return (default: 5)
        
    Returns:
        List of search results
    """
    # Mock search results for demonstration
    mock_results = [
        {
            "title": f"Search result for '{query}' - Example Site 1",
            "url": f"https://example1.com/search?q={query.replace(' ', '+')}",
            "snippet": f"This is a mock search result for the query '{query}'. In a real implementation, this would come from a search API.",
            "source": "example1.com"
        },
        {
            "title": f"'{query}' - Documentation and Guide",
            "url": f"https://docs.example.com/{query.replace(' ', '-').lower()}",
            "snippet": f"Comprehensive documentation and guide about {query}. Learn everything you need to know.",
            "source": "docs.example.com"
        },
        {
            "title": f"Latest news about {query}",
            "url": f"https://news.example.com/articles/{query.replace(' ', '-')}",
            "snippet": f"Recent developments and news related to {query}. Stay updated with the latest information.",
            "source": "news.example.com"
        }
    ]
    
    # Return requested number of results
    return mock_results[:num_results]


@mcp.tool()
def check_website_status(url: str) -> Dict[str, Any]:
    """
    Check if a website is accessible and get basic information.
    
    Args:
        url: The URL to check
        
    Returns:
        Dictionary containing website status information
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"error": "Invalid URL format"}
        
        # Make HEAD request first (faster)
        headers = {
            "User-Agent": "WriteSense-Agent/1.0 (MCP Web Server)"
        }
        
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        return {
            "url": url,
            "status_code": response.status_code,
            "status": "accessible" if response.status_code < 400 else "error",
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
            "content_type": response.headers.get("content-type", ""),
            "server": response.headers.get("server", ""),
            "final_url": response.url,
            "redirected": response.url != url,
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "url": url,
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def extract_text_content(url: str, max_length: int = 2000) -> Dict[str, Any]:
    """
    Extract clean text content from a webpage.
    
    Args:
        url: The URL to extract text from
        max_length: Maximum length of extracted text (default: 2000)
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    try:
        # Fetch the page
        result = fetch_url(url)
        if "error" in result:
            return {"error": result["error"]}
        
        content = result["content"]
        
        # Simple text extraction (remove HTML tags)
        # In production, use proper HTML parser like BeautifulSoup
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "No title found"
        
        return {
            "url": url,
            "title": title,
            "text_content": text[:max_length],
            "full_length": len(text),
            "truncated": len(text) > max_length,
            "word_count": len(text.split()),
        }
        
    except Exception as e:
        return {"error": f"Failed to extract text: {str(e)}"}


# Add a resource for URL content
@mcp.resource("web://{url}")
def get_web_resource(url: str) -> str:
    """Get web content as a resource."""
    result = fetch_url(url)
    if "error" in result:
        return f"Error fetching {url}: {result['error']}"
    
    return f"URL: {url}\nStatus: {result['status_code']}\nContent Type: {result['content_type']}\n\nContent:\n{result['content']}"


# Run the server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Web Operations MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport method")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE transport")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Web Operations MCP Server with {args.transport} transport")
    
    # Run the server
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="sse", port=args.port) 