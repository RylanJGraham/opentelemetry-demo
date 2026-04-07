"""Configuration management for the agent server."""
from dataclasses import dataclass, field
from typing import Optional, List
import os
import yaml
from pathlib import Path

# Load .env file from parent directory (react-native-explorer/)
_dotenv_path = Path(__file__).parent.parent.parent / ".env"
if _dotenv_path.exists():
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Export common constants
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


@dataclass
class AgentConfig:
    """Agent configuration."""
    # Server settings
    host: str = "127.0.0.1"
    port: int = 5100
    
    # MCP settings
    mcp_package: str = "@mobilenext/mobile-mcp@latest"
    
    # Exploration settings
    max_screens: int = 20  # Target 20 screens
    max_depth: int = 10
    action_delay_ms: int = 2000
    max_duration_seconds: float = 900  # 15 minutes
    strategy: str = "bfs"
    enable_back_navigation: bool = True
    
    # AI Vision settings
    openrouter_api_key: Optional[str] = None
    vision_model: str = "openai/gpt-4o-mini"
    use_ai_vision: bool = True
    phash_threshold: float = 0.95  # Perceptual hash similarity threshold
    ai_cache_enabled: bool = True
    
    # Cost control
    max_ai_calls_per_session: int = 100
    enable_cost_tracking: bool = True
    
    # Storage
    database_path: str = "./storage/agent.db"
    screenshots_dir: str = "./storage/screenshots"
    
    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Load config from YAML file."""
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            # Filter to only known fields
            known_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_fields}
            return cls(**filtered)
        return cls()
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables."""
        def env_bool(key: str, default: bool) -> bool:
            val = os.getenv(key)
            if val is None:
                return default
            return val.lower() in ('true', '1', 'yes', 'on')
        
        return cls(
            host=os.getenv("AGENT_HOST", "127.0.0.1"),
            port=int(os.getenv("AGENT_PORT", "5100")),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            max_screens=int(os.getenv("MAX_SCREENS", "50")),
            max_depth=int(os.getenv("MAX_DEPTH", "10")),
            action_delay_ms=int(os.getenv("ACTION_DELAY_MS", "1500")),
            strategy=os.getenv("EXPLORATION_STRATEGY", "bfs"),
            vision_model=os.getenv("VISION_MODEL", "openai/gpt-4o-mini"),
            use_ai_vision=env_bool("USE_AI_VISION", True),
            phash_threshold=float(os.getenv("PHASH_THRESHOLD", "0.95")),
            ai_cache_enabled=env_bool("AI_CACHE_ENABLED", True),
            enable_cost_tracking=env_bool("ENABLE_COST_TRACKING", True),
            database_path=os.getenv("DATABASE_PATH", "./storage/agent.db"),
            screenshots_dir=os.getenv("SCREENSHOTS_DIR", "./storage/screenshots"),
        )
