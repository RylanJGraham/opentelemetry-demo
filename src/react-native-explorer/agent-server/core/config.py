"""Configuration management for the agent server."""
from dataclasses import dataclass
from typing import Optional
import os
import yaml


@dataclass
class AgentConfig:
    """Agent configuration."""
    # Server settings
    host: str = "127.0.0.1"
    port: int = 5100
    
    # MCP settings
    mcp_package: str = "@mobilenext/mobile-mcp@latest"
    
    # Exploration settings
    max_screens: int = 50
    action_delay_ms: int = 1500
    strategy: str = "bfs"
    
    # AI settings
    openrouter_api_key: Optional[str] = None
    vision_model: str = "openai/gpt-4o-mini"
    
    # Storage
    database_path: str = "./storage/agent.db"
    screenshots_dir: str = "./storage/screenshots"
    
    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Load config from YAML file."""
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            return cls(**data)
        return cls()
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables."""
        return cls(
            host=os.getenv("AGENT_HOST", "127.0.0.1"),
            port=int(os.getenv("AGENT_PORT", "5100")),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            max_screens=int(os.getenv("MAX_SCREENS", "50")),
        )
