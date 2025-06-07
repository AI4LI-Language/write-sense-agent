#!/usr/bin/env python3
"""
Example MCP server for document operations.

This server provides tools for document search, retrieval, and processing.
It demonstrates how to create a FastMCP server that can be used by the
WriteSense Agent system.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Document Operations Server")

# Mock document database (in production, this would be a real database/vector store)
MOCK_DOCUMENTS = {
    "doc1": {
        "title": "AI and Machine Learning Overview",
        "content": "Artificial Intelligence and Machine Learning are transformative technologies that enable computers to learn and make decisions from data without explicit programming...",
        "tags": ["AI", "ML", "technology"],
        "created": "2024-01-15",
    },
    "doc2": {
        "title": "Introduction to LangGraph",
        "content": "LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain Expression Language with the ability to coordinate multiple chains across multiple steps of computation...",
        "tags": ["LangGraph", "LangChain", "AI", "development"],
        "created": "2024-01-20",
    },
    "doc3": {
        "title": "Model Context Protocol (MCP)",
        "content": "The Model Context Protocol (MCP) is an open protocol that standardizes how AI applications and large language models connect to external data sources and tools...",
        "tags": ["MCP", "protocol", "AI", "integration"],
        "created": "2024-01-25",
    },
    "doc4": {
        "title": "Building Production AI Agents",
        "content": "Building production-ready AI agents requires careful consideration of architecture, scalability, monitoring, and deployment strategies. Key components include agent orchestration, tool management, and state persistence...",
        "tags": ["AI agents", "production", "architecture", "deployment"],
        "created": "2024-01-30",
    },
}


@mcp.tool()
def search_documents(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for documents based on a query string.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of matching documents with metadata
    """
    query_lower = query.lower()
    results = []
    
    for doc_id, doc in MOCK_DOCUMENTS.items():
        # Simple text matching (in production, use proper search/embedding)
        score = 0
        if query_lower in doc["title"].lower():
            score += 10
        if query_lower in doc["content"].lower():
            score += 5
        if any(query_lower in tag.lower() for tag in doc["tags"]):
            score += 15
        
        if score > 0:
            results.append({
                "id": doc_id,
                "title": doc["title"],
                "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                "tags": doc["tags"],
                "created": doc["created"],
                "score": score,
            })
    
    # Sort by score and limit results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


@mcp.tool()
def get_document(document_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific document by its ID.
    
    Args:
        document_id: The ID of the document to retrieve
        
    Returns:
        Document data or error message
    """
    if document_id in MOCK_DOCUMENTS:
        doc = MOCK_DOCUMENTS[document_id].copy()
        doc["id"] = document_id
        return doc
    else:
        return {"error": f"Document with ID '{document_id}' not found"}


@mcp.tool()
def list_documents(tag_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available documents, optionally filtered by tag.
    
    Args:
        tag_filter: Optional tag to filter documents by
        
    Returns:
        List of document summaries
    """
    results = []
    
    for doc_id, doc in MOCK_DOCUMENTS.items():
        # Apply tag filter if specified
        if tag_filter and not any(tag_filter.lower() in tag.lower() for tag in doc["tags"]):
            continue
        
        results.append({
            "id": doc_id,
            "title": doc["title"],
            "tags": doc["tags"],
            "created": doc["created"],
            "content_preview": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
        })
    
    return results


@mcp.tool()
def get_document_tags() -> List[str]:
    """
    Get all unique tags from all documents.
    
    Returns:
        List of all unique tags
    """
    all_tags = set()
    for doc in MOCK_DOCUMENTS.values():
        all_tags.update(doc["tags"])
    
    return sorted(list(all_tags))


@mcp.tool()
def analyze_document_content(document_id: str, analysis_type: str = "summary") -> Dict[str, Any]:
    """
    Analyze document content in various ways.
    
    Args:
        document_id: The ID of the document to analyze
        analysis_type: Type of analysis to perform ("summary", "keywords", "statistics")
        
    Returns:
        Analysis results
    """
    if document_id not in MOCK_DOCUMENTS:
        return {"error": f"Document with ID '{document_id}' not found"}
    
    doc = MOCK_DOCUMENTS[document_id]
    content = doc["content"]
    
    if analysis_type == "summary":
        # Simple summary (first sentence + word count)
        sentences = content.split(". ")
        summary = sentences[0] + "." if sentences else content
        return {
            "document_id": document_id,
            "title": doc["title"],
            "summary": summary,
            "word_count": len(content.split()),
            "character_count": len(content),
        }
    
    elif analysis_type == "keywords":
        # Extract potential keywords (words longer than 4 characters, excluding common words)
        common_words = {"that", "with", "from", "they", "have", "this", "will", "been", "were", "said", "each", "which", "their", "what", "about", "would", "there", "could", "other", "more", "very", "time", "when", "much", "these", "your", "some", "just", "first", "into", "over", "think", "also", "back", "after", "good", "most", "know", "where", "work", "only", "little", "long", "make", "year", "come", "people", "well", "between", "through", "before", "during", "without", "since", "under", "while", "should", "might", "place", "right", "great", "small", "large", "never", "again", "within", "along", "still", "every", "around", "being", "below", "above", "across", "until", "against", "upon", "always", "almost", "another", "together", "getting", "something", "nothing", "everything", "anything", "someone", "everyone", "anyone"}
        
        words = content.lower().replace(",", "").replace(".", "").replace("(", "").replace(")", "").split()
        keywords = [word for word in words if len(word) > 4 and word not in common_words]
        
        # Count frequency
        keyword_freq = {}
        for word in keywords:
            keyword_freq[word] = keyword_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "document_id": document_id,
            "title": doc["title"],
            "top_keywords": sorted_keywords[:10],
            "total_unique_keywords": len(keyword_freq),
        }
    
    elif analysis_type == "statistics":
        words = content.split()
        sentences = content.split(". ")
        paragraphs = content.split("\n\n")
        
        return {
            "document_id": document_id,
            "title": doc["title"],
            "statistics": {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "paragraph_count": len(paragraphs),
                "character_count": len(content),
                "character_count_no_spaces": len(content.replace(" ", "")),
                "average_words_per_sentence": round(len(words) / max(len(sentences), 1), 2),
                "average_characters_per_word": round(len(content.replace(" ", "")) / max(len(words), 1), 2),
            }
        }
    
    else:
        return {"error": f"Unknown analysis type: {analysis_type}. Supported types: summary, keywords, statistics"}


# Add a dynamic resource for document content
@mcp.resource("document://{document_id}")
def get_document_resource(document_id: str) -> str:
    """Get document content as a resource."""
    if document_id in MOCK_DOCUMENTS:
        doc = MOCK_DOCUMENTS[document_id]
        return f"Title: {doc['title']}\n\nContent:\n{doc['content']}\n\nTags: {', '.join(doc['tags'])}\nCreated: {doc['created']}"
    else:
        return f"Document '{document_id}' not found"


# Run the server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Document Operations MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport method")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Document Operations MCP Server with {args.transport} transport")
    
    # Add sample data loading capability
    sample_data_path = Path("sample_documents.json")
    if sample_data_path.exists():
        try:
            with open(sample_data_path, "r") as f:
                additional_docs = json.load(f)
                MOCK_DOCUMENTS.update(additional_docs)
                logger.info(f"Loaded {len(additional_docs)} additional documents from {sample_data_path}")
        except Exception as e:
            logger.warning(f"Could not load additional documents: {e}")
    
    # Run the server
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="sse", port=args.port) 