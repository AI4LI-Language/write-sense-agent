"""
WriteSense Agent - LangGraph-based agent system with MCP orchestration.

A production-ready agent framework that orchestrates multiple MCP (Model Context Protocol)
servers through a hierarchical agent architecture with React agents.
"""

from write_sense_agent.core.orchestrator import OrchestratorAgent
from write_sense_agent.core.mcp_agent import MCPAgent
from write_sense_agent.core.config import AgentConfig

__version__ = "0.1.0"
__all__ = ["OrchestratorAgent", "MCPAgent", "AgentConfig"] 