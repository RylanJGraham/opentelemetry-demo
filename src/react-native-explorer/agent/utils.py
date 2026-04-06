"""
Shared utilities for the React Native Explorer Agent.
Config loading, logging, image processing.
"""

import base64
import io
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from PIL import Image
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# ── Rich console with custom theme ─────────────────────────────────
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "explore": "bold magenta",
})

console = Console(theme=custom_theme)

# ── Logging ─────────────────────────────────────────────────────────

def setup_logging(log_dir: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    """Configure Rich logging with optional file output."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers: list[logging.Handler] = [
        RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
    ]

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_dir / f"explorer_{timestamp}.log", encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    logger = logging.getLogger("explorer")
    logger.setLevel(level)
    return logger


# ── Config ──────────────────────────────────────────────────────────

class Config:
    """Loads and provides access to config.yaml + environment variables."""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()

        config_file = Path(config_path)
        if not config_file.exists():
            console.print(f"[error]Config file not found: {config_path}[/error]")
            sys.exit(1)

        with open(config_file, "r") as f:
            self._data = yaml.safe_load(f)

        # Resolve API key from environment
        api_key_env = self._data.get("vision", {}).get("api_key_env", "OPENROUTER_API_KEY")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv(api_key_env, "")
        if not self.api_key:
            console.print("[error]OPENROUTER_API_KEY not set in environment or .env[/error]")
            sys.exit(1)

        # Ensure storage directories exist
        for dir_key in ["screenshots_dir", "stories_dir"]:
            dir_path = Path(self._data["storage"].get(dir_key, f"./storage/{dir_key}"))
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def app(self) -> dict:
        return self._data.get("app", {})

    @property
    def exploration(self) -> dict:
        return self._data.get("exploration", {})

    @property
    def vision(self) -> dict:
        return self._data.get("vision", {})

    @property
    def storage(self) -> dict:
        return self._data.get("storage", {})

    @property
    def server(self) -> dict:
        return self._data.get("server", {})

    @property
    def ui(self) -> dict:
        return self._data.get("ui", {})

    def get(self, dotpath: str, default: Any = None) -> Any:
        """Get a nested config value using dot notation, e.g. 'exploration.max_screens'."""
        keys = dotpath.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val


# ── Image utilities ─────────────────────────────────────────────────

def resize_screenshot(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Resize a screenshot to fit within max_size while preserving aspect ratio."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size

    if max(w, h) <= max_size:
        return image_bytes

    if w > h:
        new_w = max_size
        new_h = int(h * (max_size / w))
    else:
        new_h = max_size
        new_w = int(w * (max_size / h))

    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 data URI string."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def base64_to_image(data_uri: str) -> bytes:
    """Convert base64 data URI back to image bytes."""
    if data_uri.startswith("data:"):
        data_uri = data_uri.split(",", 1)[1]
    return base64.b64decode(data_uri)


def save_screenshot(image_bytes: bytes, path: Path) -> Path:
    """Save screenshot bytes to a file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def generate_screen_id() -> str:
    """Generate a unique screen ID based on timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def save_exploration_state(state: dict, path: Path):
    """Persist current exploration state to JSON for resume support."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_exploration_state(path: Path) -> Optional[dict]:
    """Load saved exploration state if it exists."""
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None
