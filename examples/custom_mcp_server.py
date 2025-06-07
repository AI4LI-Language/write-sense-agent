#!/usr/bin/env python3
"""
Example of creating a custom MCP server for WriteSense Agent.

This example shows how to create a custom MCP server with tools
and resources that can be integrated into the agent system.
"""

import json
import logging
import math
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Custom Analytics Server")

# Mock data store
ANALYTICS_DATA = {
    "users": [
        {"id": 1, "name": "Alice", "age": 28, "city": "New York", "signup_date": "2024-01-15"},
        {"id": 2, "name": "Bob", "age": 34, "city": "San Francisco", "signup_date": "2024-01-20"},
        {"id": 3, "name": "Charlie", "age": 25, "city": "Chicago", "signup_date": "2024-01-25"},
        {"id": 4, "name": "Diana", "age": 31, "city": "Boston", "signup_date": "2024-02-01"},
        {"id": 5, "name": "Eve", "age": 29, "city": "Seattle", "signup_date": "2024-02-05"},
    ],
    "events": [
        {"user_id": 1, "event": "login", "timestamp": "2024-02-10T10:00:00Z"},
        {"user_id": 1, "event": "page_view", "timestamp": "2024-02-10T10:05:00Z"},
        {"user_id": 2, "event": "login", "timestamp": "2024-02-10T11:00:00Z"},
        {"user_id": 3, "event": "purchase", "timestamp": "2024-02-10T12:00:00Z", "amount": 99.99},
        {"user_id": 1, "event": "logout", "timestamp": "2024-02-10T13:00:00Z"},
    ]
}


@mcp.tool()
def get_user_stats() -> Dict[str, Any]:
    """
    Get basic user statistics.
    
    Returns:
        Dictionary containing user statistics
    """
    users = ANALYTICS_DATA["users"]
    
    ages = [user["age"] for user in users]
    cities = [user["city"] for user in users]
    
    return {
        "total_users": len(users),
        "average_age": round(sum(ages) / len(ages), 1),
        "age_range": {"min": min(ages), "max": max(ages)},
        "cities": list(set(cities)),
        "users_by_city": {city: cities.count(city) for city in set(cities)},
    }


@mcp.tool()
def get_user_by_id(user_id: int) -> Dict[str, Any]:
    """
    Get user information by ID.
    
    Args:
        user_id: The ID of the user to retrieve
        
    Returns:
        User information or error message
    """
    users = ANALYTICS_DATA["users"]
    user = next((u for u in users if u["id"] == user_id), None)
    
    if user:
        return user
    else:
        return {"error": f"User with ID {user_id} not found"}


@mcp.tool()
def search_users(query: str) -> List[Dict[str, Any]]:
    """
    Search users by name or city.
    
    Args:
        query: Search query (name or city)
        
    Returns:
        List of matching users
    """
    users = ANALYTICS_DATA["users"]
    query_lower = query.lower()
    
    matching_users = []
    for user in users:
        if (query_lower in user["name"].lower() or 
            query_lower in user["city"].lower()):
            matching_users.append(user)
    
    return matching_users


@mcp.tool()
def get_event_stats(event_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get event statistics, optionally filtered by event type.
    
    Args:
        event_type: Optional event type to filter by
        
    Returns:
        Event statistics
    """
    events = ANALYTICS_DATA["events"]
    
    if event_type:
        filtered_events = [e for e in events if e["event"] == event_type]
    else:
        filtered_events = events
    
    event_types = [e["event"] for e in filtered_events]
    event_counts = {event: event_types.count(event) for event in set(event_types)}
    
    # Calculate revenue for purchase events
    purchase_events = [e for e in filtered_events if e["event"] == "purchase"]
    total_revenue = sum(e.get("amount", 0) for e in purchase_events)
    
    return {
        "total_events": len(filtered_events),
        "event_types": event_counts,
        "total_revenue": total_revenue,
        "purchase_count": len(purchase_events),
        "average_purchase": round(total_revenue / len(purchase_events), 2) if purchase_events else 0,
    }


@mcp.tool()
def generate_report(report_type: str = "summary") -> Dict[str, Any]:
    """
    Generate various types of analytics reports.
    
    Args:
        report_type: Type of report ("summary", "detailed", "revenue")
        
    Returns:
        Generated report
    """
    if report_type == "summary":
        user_stats = get_user_stats()
        event_stats = get_event_stats()
        
        return {
            "report_type": "summary",
            "generated_at": datetime.now().isoformat(),
            "user_summary": user_stats,
            "event_summary": event_stats,
            "key_metrics": {
                "users_per_city": user_stats["users_by_city"],
                "total_revenue": event_stats["total_revenue"],
                "events_per_user": round(event_stats["total_events"] / user_stats["total_users"], 1),
            }
        }
    
    elif report_type == "detailed":
        return {
            "report_type": "detailed",
            "generated_at": datetime.now().isoformat(),
            "users": ANALYTICS_DATA["users"],
            "events": ANALYTICS_DATA["events"],
            "analysis": {
                "most_active_user": _get_most_active_user(),
                "popular_events": _get_popular_events(),
            }
        }
    
    elif report_type == "revenue":
        purchase_events = [e for e in ANALYTICS_DATA["events"] if e["event"] == "purchase"]
        
        return {
            "report_type": "revenue",
            "generated_at": datetime.now().isoformat(),
            "total_revenue": sum(e.get("amount", 0) for e in purchase_events),
            "purchase_count": len(purchase_events),
            "purchases": purchase_events,
        }
    
    else:
        return {"error": f"Unknown report type: {report_type}. Available types: summary, detailed, revenue"}


@mcp.tool()
def calculate_metrics(metric_type: str, values: List[float]) -> Dict[str, Any]:
    """
    Calculate various statistical metrics.
    
    Args:
        metric_type: Type of metric ("basic", "advanced")
        values: List of numerical values
        
    Returns:
        Calculated metrics
    """
    if not values:
        return {"error": "No values provided"}
    
    # Basic metrics
    basic_metrics = {
        "count": len(values),
        "sum": sum(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }
    
    if metric_type == "basic":
        return basic_metrics
    
    elif metric_type == "advanced":
        # Calculate additional metrics
        mean = basic_metrics["mean"]
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # Median
        sorted_values = sorted(values)
        n = len(sorted_values)
        median = (sorted_values[n//2] + sorted_values[(n-1)//2]) / 2
        
        return {
            **basic_metrics,
            "median": median,
            "variance": variance,
            "std_dev": std_dev,
            "coefficient_of_variation": std_dev / mean if mean != 0 else 0,
        }
    
    else:
        return {"error": f"Unknown metric type: {metric_type}. Available types: basic, advanced"}


def _get_most_active_user() -> Dict[str, Any]:
    """Helper function to find the most active user."""
    events = ANALYTICS_DATA["events"]
    user_event_counts = {}
    
    for event in events:
        user_id = event["user_id"]
        user_event_counts[user_id] = user_event_counts.get(user_id, 0) + 1
    
    if not user_event_counts:
        return {"error": "No events found"}
    
    most_active_user_id = max(user_event_counts, key=user_event_counts.get)
    user = next(u for u in ANALYTICS_DATA["users"] if u["id"] == most_active_user_id)
    
    return {
        "user": user,
        "event_count": user_event_counts[most_active_user_id]
    }


def _get_popular_events() -> Dict[str, int]:
    """Helper function to get popular events."""
    events = ANALYTICS_DATA["events"]
    event_types = [e["event"] for e in events]
    return {event: event_types.count(event) for event in set(event_types)}


# Add resources for data access
@mcp.resource("analytics://users")
def get_users_resource() -> str:
    """Get all users as a resource."""
    users = ANALYTICS_DATA["users"]
    return json.dumps(users, indent=2)


@mcp.resource("analytics://events")
def get_events_resource() -> str:
    """Get all events as a resource."""
    events = ANALYTICS_DATA["events"]
    return json.dumps(events, indent=2)


@mcp.resource("analytics://summary")
def get_summary_resource() -> str:
    """Get analytics summary as a resource."""
    summary = generate_report("summary")
    return json.dumps(summary, indent=2)


# Run the server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Custom Analytics MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport method")
    parser.add_argument("--port", type=int, default=8002, help="Port for SSE transport")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Custom Analytics MCP Server with {args.transport} transport")
    
    # Run the server
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="sse", port=args.port) 