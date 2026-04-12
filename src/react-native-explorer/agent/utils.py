"""
Shared utilities for the React Native Explorer Agent.
Config loading, logging, image processing, perceptual hashing, and smart caching.
"""

import base64
import hashlib
import io
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

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
    "cache": "dim cyan",
    "ai": "bold yellow",
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
        
        self.config_path = config_path

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
        for dir_key in ["screenshots_dir", "stories_dir", "cache_dir"]:
            dir_path = Path(self._data.get("storage", {}).get(dir_key, f"./storage/{dir_key}"))
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


# ── Perceptual Hashing for Smart Caching ────────────────────────────

def compute_phash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Compute perceptual hash (dHash) for image similarity comparison.
    Much faster than pixel-wise comparison and resistant to minor changes.
    """
    img = Image.open(io.BytesIO(image_bytes))
    # Convert to grayscale and resize
    img = img.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = list(img.getdata())
    
    # Compute difference hash
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            left_pixel = pixels[row * (hash_size + 1) + col]
            right_pixel = pixels[row * (hash_size + 1) + col + 1]
            diff.append(left_pixel > right_pixel)
    
    # Convert to hex string
    decimal_value = sum(bit << i for i, bit in enumerate(diff))
    return f"{decimal_value:0{hash_size * hash_size // 4}x}"


def compute_content_hash(image_bytes: bytes) -> str:
    """Compute SHA-256 hash of image content for exact matching."""
    return hashlib.sha256(image_bytes).hexdigest()


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two perceptual hashes."""
    if len(hash1) != len(hash2):
        return float('inf')
    x = int(hash1, 16) ^ int(hash2, 16)
    return bin(x).count('1')


def are_images_similar(phash1: str, phash2: str, threshold: int = 5) -> bool:
    """
    Check if two images are similar based on perceptual hash.
    Threshold of 5 means ~10% bit difference allowed.
    """
    return hamming_distance(phash1, phash2) <= threshold


def compute_structure_hash(elements: list[dict]) -> str:
    """
    Compute a hash of the UI element structure.
    Used to detect identical screens even with different content.
    """
    if not elements:
        return "empty"
    
    # Create structure fingerprint from element types and positions
    structure = []
    for el in sorted(elements, key=lambda e: (e.get("y", 0), e.get("x", 0))):
        structure.append(f"{el.get('type', 'unknown')}:{el.get('x', 0)//50}:{el.get('y', 0)//50}")
    
    return hashlib.sha256("|".join(structure).encode()).hexdigest()[:16]


def fast_compare_screenshots(img1_bytes: bytes, img2_bytes: bytes, threshold: float = 0.98) -> bool:
    """
    Fast comparison of two screenshots to detect UI settling.
    Returns True if images are similar enough (UI has settled).
    Uses downsampled grayscale pixel comparison for speed.
    
    Args:
        img1_bytes: First screenshot bytes
        img2_bytes: Second screenshot bytes  
        threshold: Similarity threshold (0.98 = 98% same pixels required)
    
    Returns:
        True if screens are similar (settled), False if different (still changing)
    """
    try:
        # Downsample to 64x64 grayscale for fast comparison
        size = (64, 64)
        img1 = Image.open(io.BytesIO(img1_bytes)).convert("L").resize(size, Image.NEAREST)
        img2 = Image.open(io.BytesIO(img2_bytes)).convert("L").resize(size, Image.NEAREST)
        
        px1 = list(img1.getdata())
        px2 = list(img2.getdata())
        
        if len(px1) != len(px2):
            return False
        
        # Count pixels that are close enough (within 15 brightness levels)
        close_pixels = sum(1 for a, b in zip(px1, px2) if abs(a - b) < 15)
        similarity = close_pixels / len(px1)
        
        return similarity >= threshold
    except Exception:
        return False


def ensure_adb_on_path() -> Optional[str]:
    """
    Ensure adb is available on the PATH.
    If not, search common Android SDK locations on Windows.
    Returns the path to the platform-tools directory if found and added, else None.
    """
    import shutil
    if shutil.which("adb"):
        return None

    # Common Windows locations
    potential_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools",
        Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools",
        Path(os.environ.get("PROGRAMFILES", "")) / "Android" / "Android Studio" / "sdk" / "platform-tools",
    ]

    for p in potential_paths:
        try:
            if p.exists() and (p / "adb.exe").exists():
                path_str = str(p.absolute())
                if path_str not in os.environ["PATH"]:
                    os.environ["PATH"] = path_str + os.pathsep + os.environ["PATH"]
                    print(f"[EXPLORER] 🔧 Automatically added Android SDK to PATH: {path_str}", flush=True)
                return path_str
        except Exception:
            continue

    print("[EXPLORER] ⚠️ Could not find adb.exe automatically. Please ensure Android SDK is installed.", flush=True)
    return None


# ── Smart Screen Cache ──────────────────────────────────────────────

class ScreenCache:
    """
    Multi-level caching system for screens to minimize AI API calls.
    Level 1: Exact content hash match
    Level 2: Perceptual hash match (similar appearance)
    Level 3: Structure hash match (same layout, different content)
    """
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "screen_index.json"
        self._index = self._load_index()
        
    def _load_index(self) -> dict:
        """Load the screen cache index."""
        if self.index_file.exists():
            with open(self.index_file, "r") as f:
                return json.load(f)
        return {
            "screens": {},  # screen_id -> {phash, content_hash, structure_hash, data}
            "phash_map": {},  # phash -> [screen_ids]
            "structure_map": {},  # structure_hash -> [screen_ids]
        }
    
    def _save_index(self):
        """Save the screen cache index."""
        with open(self.index_file, "w") as f:
            json.dump(self._index, f, indent=2)
    
    def find_match(
        self, 
        image_bytes: bytes, 
        elements: list[dict],
        phash_threshold: int = 5
    ) -> Tuple[Optional[str], str]:
        """
        Try to find a matching screen in cache.
        Returns: (screen_id, match_type) where match_type is 'exact', 'similar', 'structure', or None
        """
        content_hash = compute_content_hash(image_bytes)
        phash = compute_phash(image_bytes)
        structure_hash = compute_structure_hash(elements)
        
        # Level 1: Exact match
        for screen_id, data in self._index["screens"].items():
            if data.get("content_hash") == content_hash:
                return screen_id, "exact"
        
        # Level 2: Perceptual hash match
        for existing_phash, screen_ids in self._index["phash_map"].items():
            if are_images_similar(phash, existing_phash, phash_threshold):
                return screen_ids[0], "similar"
        
        # Level 3: Structure match (if elements provided)
        if elements and structure_hash in self._index["structure_map"]:
            screen_ids = self._index["structure_map"][structure_hash]
            return screen_ids[0], "structure"
        
        return None, None
    
    def add_screen(
        self, 
        screen_id: str, 
        image_bytes: bytes, 
        elements: list[dict],
        screen_data: dict
    ):
        """Add a new screen to the cache."""
        content_hash = compute_content_hash(image_bytes)
        phash = compute_phash(image_bytes)
        structure_hash = compute_structure_hash(elements)
        
        self._index["screens"][screen_id] = {
            "content_hash": content_hash,
            "phash": phash,
            "structure_hash": structure_hash,
            "data": screen_data,
            "added_at": datetime.now().isoformat(),
        }
        
        # Update reverse indexes
        if phash not in self._index["phash_map"]:
            self._index["phash_map"][phash] = []
        if screen_id not in self._index["phash_map"][phash]:
            self._index["phash_map"][phash].append(screen_id)
        
        if structure_hash not in self._index["structure_map"]:
            self._index["structure_map"][structure_hash] = []
        if screen_id not in self._index["structure_map"][structure_hash]:
            self._index["structure_map"][structure_hash].append(screen_id)
        
        self._save_index()
    
    def get_screen(self, screen_id: str) -> Optional[dict]:
        """Get cached screen data."""
        entry = self._index["screens"].get(screen_id)
        return entry["data"] if entry else None
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "total_screens": len(self._index["screens"]),
            "unique_visual": len(self._index["phash_map"]),
            "unique_structures": len(self._index["structure_map"]),
        }


# ── ID Generation ───────────────────────────────────────────────────

def generate_screen_id() -> str:
    """Generate a unique screen ID based on timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def generate_element_id(screen_id: str, index: int) -> str:
    """Generate a unique element ID."""
    return f"{screen_id}_el_{index}"


def generate_story_id() -> str:
    """Generate a unique story ID."""
    return f"story_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


# ── State Management ────────────────────────────────────────────────

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


# ── Cost Tracking ───────────────────────────────────────────────────

class CostTracker:
    """Track AI API usage and estimate costs."""
    
    # OpenRouter pricing per 1M tokens (approximate for vision models)
    PRICING = {
        "google/gemini-2.0-flash-001": {"input": 0.075, "output": 0.30},
        "google/gemini-2.0-pro": {"input": 1.25, "output": 10.0},
        "anthropic/claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
    }
    
    def __init__(self, model: str):
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.cache_hits = 0
        
    def add_request(self, input_tokens: int, output_tokens: int, cached: bool = False):
        """Record an API request."""
        if cached:
            self.cache_hits += 1
            return
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1
    
    def estimate_cost(self) -> float:
        """Estimate total cost in USD."""
        pricing = self.PRICING.get(self.model, {"input": 0.10, "output": 0.40})
        input_cost = (self.total_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.total_output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def get_stats(self) -> dict:
        """Get cost statistics."""
        return {
            "model": self.model,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(self.estimate_cost(), 4),
        }
