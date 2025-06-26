"""Configuration module for WriteSense Agent system."""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class TransportType(str, Enum):
    """Supported transport types for MCP servers."""
    
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    
    name: str = Field(..., description="Unique name for the MCP server")
    transport: TransportType = Field(..., description="Transport protocol to use")
    
    # For stdio transport
    command: Optional[str] = Field(None, description="Command to execute for stdio transport")
    args: Optional[List[str]] = Field(default_factory=list, description="Arguments for the command")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    
    # For SSE/HTTP transport
    url: Optional[str] = Field(None, description="URL for SSE/HTTP transport")
    
    # Additional configuration
    timeout: int = Field(30, description="Connection timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of connection retries")
    
    @validator("command", always=True)
    def validate_stdio_config(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate that stdio transport has required command."""
        transport = values.get("transport")
        if transport == TransportType.STDIO and not v:
            raise ValueError("command is required for stdio transport")
        return v
    
    @validator("url", always=True)
    def validate_url_config(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate that SSE/HTTP transport has required URL."""
        transport = values.get("transport")
        if transport in (TransportType.SSE, TransportType.STREAMABLE_HTTP) and not v:
            raise ValueError("url is required for SSE/HTTP transport")
        return v


class LLMConfig(BaseModel):
    """Configuration for language model."""
    
    provider: ModelProvider = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4000, ge=1, le=100000, description="Maximum tokens")
    timeout: int = Field(60, description="Request timeout in seconds")
    
    # API configuration
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    
    @validator("api_key", always=True)
    def validate_api_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate API key configuration."""
        if not v:
            provider = values.get("provider")
            env_var = f"{provider.upper()}_API_KEY" if provider else "API_KEY"
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"API key not found in environment variable {env_var}")
            return api_key
        return v


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator agent."""
    
    system_prompt: str = Field(
        "You are the WriteSense Agent, an intelligent assistant specifically designed to help people with "
        "disabilities create and work with documents. Your primary purpose is to assist users in writing reports, "
        "diaries, and other types of documents through natural interaction with humans.\n\n"
        "IMPORTANT: YOU MUST ALWAYS RESPOND TO USERS IN VIETNAMESE regardless of what language they use to communicate with you.\n\n"
        "CRITICAL RESPONSE FORMAT REQUIREMENT:\n"
        "YOU MUST ALWAYS reply the final result using EXACTLY this format - no exceptions:\n\n"
        "Action: <action type>\n"
        "Action content: <action content>\n"
        "Answer: <answer>\n\n"
        "Available action types:\n"
        "DOCUMENT MANAGEMENT:\n"
        "- create_doc: Create a completely new document from scratch\n"
        "- set_title_doc: Set or change the title/name of the entire document\n"
        "- read_title_doc: Read the current title/name of the document\n"
        "- save_doc: Save the current document to storage\n"
        "- remove_doc: Delete/remove the entire document permanently\n\n"
        "PAGE CREATION & NAVIGATION:\n"
        "- add_page: CREATE A NEW PAGE and automatically switch to it (use when user wants to add/create a new page)\n"
        "- next_page: NAVIGATE to the next existing page (use only for moving between existing pages)\n"
        "- prev_page: NAVIGATE to the previous existing page (use only for moving between existing pages)\n"
        "- delete_page: Delete/remove a specific page from the document\n\n"
        "PAGE CONTENT OPERATIONS:\n"
        "- add_to_page: ADD/APPEND new content to the current page (keeps existing content)\n"
        "- rewrite_page: COMPLETELY REPLACE all content on the current page (removes existing content)\n"
        "- read_page: Read the content of the current page\n"
        "- set_title_page: Set or change the title/header of the current page only\n"
        "- read_title_page: Read the title/header of the current page\n\n"
        "COMMUNICATION:\n"
        "- reply_user: Just reply to user with conversational content, without making any document changes\n\n"

        "SUB-AGENT DELEGATION GUIDELINES:\n"
        "You have access to specialized sub-agents with specific capabilities. However, you should be selective about when to use them:\n\n"
        "DELEGATE TO SUB-AGENTS ONLY WHEN:\n"
        "- The user specifically requests a complex task that requires specialized knowledge\n"
        "- You need additional information or capabilities that you don't have\n"
        "- The task clearly benefits from a specific sub-agent's expertise\n\n"
        "DO NOT DELEGATE TO SUB-AGENTS WHEN:\n"
        "- You can handle simple conversations, greetings, or basic questions directly\n"
        "- The user is just asking general questions about your capabilities\n"
        "- Simple document operations can be done without specialized tools\n"
        "- The request is straightforward and doesn't require external data or complex processing\n\n"
        "DISABILITY SUPPORT GUIDELINES:\n"
        "- Use simple and clear language that is easy to understand\n"
        "- Provide detailed step-by-step instructions when needed\n"
        "- Be patient and supportive throughout the document creation process\n"
        "- Suggest alternative approaches to complete tasks when appropriate\n"
        "- Always confirm understanding before proceeding to the next step\n"
        "- Break down complex tasks into smaller, manageable parts\n"
        "- Offer encouragement and positive reinforcement\n"
        "- Be flexible and adapt to different user needs and abilities\n\n"
        "Remember: Handle simple requests directly and only use sub-agents when their specialized capabilities are truly needed. "
        "Always follow the exact Action/Content format in Vietnamese.",
        description="Base system prompt for the orchestrator (delegation guidelines are added dynamically)"
    )
    max_iterations: int = Field(10, ge=1, le=50, description="Maximum orchestration iterations")
    enable_memory: bool = Field(True, description="Enable conversation memory")
    memory_max_tokens: int = Field(4000, description="Maximum tokens for memory")


class AgentConfig(BaseModel):
    """Main configuration for the WriteSense Agent system."""
    
    # LLM configurations - separate models for different agent types
    orchestrator_llm: LLMConfig = Field(..., description="Language model configuration for orchestrator agent")
    mcp_agents_llm: LLMConfig = Field(..., description="Language model configuration for MCP agents")
    
    # MCP servers configuration
    mcp_servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, 
        description="MCP server configurations"
    )
    
    # Orchestrator configuration
    orchestrator: OrchestratorConfig = Field(
        default_factory=OrchestratorConfig,
        description="Orchestrator agent configuration"
    )
    
    # General settings
    debug: bool = Field(False, description="Enable debug mode")
    log_level: str = Field("INFO", description="Logging level")
    recursion_limit: int = Field(50, ge=1, le=200, description="LangGraph recursion limit")
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables."""
        # Orchestrator LLM configuration (more powerful model)
        orchestrator_provider = ModelProvider(os.getenv("ORCHESTRATOR_LLM_PROVIDER", "openai"))
        orchestrator_model = os.getenv("ORCHESTRATOR_LLM_MODEL", "gpt-4o")
        
        orchestrator_llm_config = LLMConfig(
            provider=orchestrator_provider,
            model=orchestrator_model,
            temperature=float(os.getenv("ORCHESTRATOR_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("ORCHESTRATOR_LLM_MAX_TOKENS", "4000")),
        )
        
        # MCP agents LLM configuration (can be faster/cheaper model)
        mcp_provider = ModelProvider(os.getenv("MCP_AGENTS_LLM_PROVIDER", "openai"))
        mcp_model = os.getenv("MCP_AGENTS_LLM_MODEL", "gpt-4o-mini")
        
        mcp_agents_llm_config = LLMConfig(
            provider=mcp_provider,
            model=mcp_model,
            temperature=float(os.getenv("MCP_AGENTS_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("MCP_AGENTS_LLM_MAX_TOKENS", "2000")),
        )
        
        # Basic configuration
        config = cls(
            orchestrator_llm=orchestrator_llm_config,
            mcp_agents_llm=mcp_agents_llm_config,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
        
        return config
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "AgentConfig":
        """Load configuration from a JSON/YAML file."""
        import json
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with config_path.open("r") as f:
            if config_path.suffix.lower() == ".json":
                data = json.load(f)
            else:
                # For YAML support, you'd need to install PyYAML
                raise ValueError("Only JSON configuration files are currently supported")
        
        return cls(**data)
    
    def add_mcp_server(
        self,
        name: str,
        transport: TransportType,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add an MCP server configuration."""
        server_config = MCPServerConfig(
            name=name,
            transport=transport,
            command=command,
            args=args or [],
            url=url,
            **kwargs,
        )
        self.mcp_servers[name] = server_config
    
    def get_langgraph_config(self) -> Dict[str, Any]:
        """Get configuration dict for LangGraph."""
        return {
            "recursion_limit": self.recursion_limit,
            "debug": self.debug,
        } 