"""Exploration engine - the brain of the agent."""
import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from core.database import db
from mcp_client.client import MCPClient

logger = logging.getLogger("agent.explorer")


class ExplorationState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    EXPLORING = "exploring"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class ExplorationStats:
    screens_found: int = 0
    transitions_found: int = 0
    actions_taken: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time


@dataclass 
class Screen:
    id: str
    name: str
    screen_type: str
    description: str
    screenshot_path: str
    elements: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class ExplorationEngine:
    """Main exploration engine."""
    
    def __init__(self, config: Any):
        self.config = config
        self.mcp = MCPClient()
        self.state = ExplorationState.IDLE
        self.stats = ExplorationStats()
        self.current_screen_id: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self._stop_event = asyncio.Event()
        self._callbacks: List[callable] = []
    
    def on_state_change(self, callback: callable):
        """Register state change callback."""
        self._callbacks.append(callback)
    
    def _notify(self, event: str, data: Any = None):
        """Notify all callbacks."""
        for cb in self._callbacks:
            try:
                asyncio.create_task(cb(event, data))
            except Exception:
                pass
    
    async def start(self):
        """Start exploration."""
        if self.state == ExplorationState.EXPLORING:
            return {"status": "already_running"}
        
        self.state = ExplorationState.CONNECTING
        self._notify("state_change", {"state": self.state.value})
        
        # Connect to MCP
        connected = await self.mcp.connect()
        if not connected:
            self.state = ExplorationState.ERROR
            self._notify("state_change", {"state": self.state.value, "error": "MCP connection failed"})
            return {"status": "error", "message": "Failed to connect to MCP"}
        
        # Start exploration loop
        self.state = ExplorationState.EXPLORING
        self.stats.start_time = time.time()
        self._stop_event.clear()
        self._pause_event.set()
        self._task = asyncio.create_task(self._exploration_loop())
        
        self._notify("state_change", {"state": self.state.value})
        return {"status": "started"}
    
    async def pause(self):
        """Pause exploration."""
        if self.state == ExplorationState.EXPLORING:
            self._pause_event.clear()
            self.state = ExplorationState.PAUSED
            self._notify("state_change", {"state": self.state.value})
        return {"status": "paused"}
    
    async def resume(self):
        """Resume exploration."""
        if self.state == ExplorationState.PAUSED:
            self._pause_event.set()
            self.state = ExplorationState.EXPLORING
            self._notify("state_change", {"state": self.state.value})
        return {"status": "resumed"}
    
    async def stop(self):
        """Stop exploration."""
        self._stop_event.set()
        self._pause_event.set()  # Ensure loop can exit
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.mcp.disconnect()
        
        self.state = ExplorationState.IDLE
        self.stats.end_time = time.time()
        self._notify("state_change", {"state": self.state.value})
        return {"status": "stopped"}
    
    async def _exploration_loop(self):
        """Main exploration loop."""
        try:
            while not self._stop_event.is_set():
                # Check pause
                if not self._pause_event.is_set():
                    await self._pause_event.wait()
                    if self._stop_event.is_set():
                        break
                
                # Check screen limit
                if self.stats.screens_found >= self.config.max_screens:
                    logger.info(f"Reached max screens limit: {self.config.max_screens}")
                    break
                
                # Capture screen
                await self._explore_step()
                
                # Small delay between actions
                await asyncio.sleep(self.config.action_delay_ms / 1000)
                
        except asyncio.CancelledError:
            logger.info("Exploration loop cancelled")
        except Exception as e:
            logger.exception("Exploration error")
            self.state = ExplorationState.ERROR
            self._notify("state_change", {"state": self.state.value, "error": str(e)})
        finally:
            self.stats.end_time = time.time()
            if self.state != ExplorationState.ERROR:
                self.state = ExplorationState.COMPLETE
            self._notify("exploration_complete", {"stats": self._stats_dict()})
    
    async def _explore_step(self):
        """Single exploration step."""
        # Take screenshot
        screenshot = await self.mcp.take_screenshot()
        if not screenshot:
            logger.warning("Failed to capture screenshot")
            return
        
        # Get elements
        elements = await self.mcp.list_elements()
        
        # Generate screen ID from screenshot hash
        import hashlib
        screen_id = f"screen_{hashlib.md5(screenshot).hexdigest()[:12]}"
        
        # Check if screen already exists
        existing = await db.fetchone("SELECT * FROM screens WHERE id = ?", (screen_id,))
        
        if existing:
            # Update visit count
            await db.execute(
                "UPDATE screens SET visit_count = visit_count + 1, last_seen = ? WHERE id = ?",
                (time.time(), screen_id)
            )
            await db.commit()
        else:
            # Save screenshot
            screenshot_path = f"{screen_id}.png"
            screenshot_dir = Path(self.config.screenshots_dir)
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            (screenshot_dir / screenshot_path).write_bytes(screenshot)
            
            # Analyze with AI (placeholder - would call vision model here)
            screen_name = f"Screen {self.stats.screens_found + 1}"
            screen_type = "unknown"
            
            # Insert new screen
            await db.execute(
                """INSERT INTO screens (id, name, screen_type, description, screenshot_path, 
                   element_count, first_seen, last_seen, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (screen_id, screen_name, screen_type, "", screenshot_path, 
                 len(elements), time.time(), time.time(), json.dumps({}))
            )
            
            # Insert elements
            for i, el in enumerate(elements):
                el_id = f"{screen_id}_el_{i}"
                await db.execute(
                    """INSERT INTO elements (id, screen_id, element_type, label, x, y, 
                       width, height, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (el_id, screen_id, 
                     el.get("type", "unknown"), 
                     el.get("label", "")[:100],
                     int(el.get("x", 0)), int(el.get("y", 0)),
                     int(el.get("width", 0)), int(el.get("height", 0)),
                     el.get("confidence", 1.0))
                )
            
            await db.commit()
            
            self.stats.screens_found += 1
            self._notify("new_screen", {
                "id": screen_id,
                "name": screen_name,
                "type": screen_type,
                "screenshot": screenshot_path,
                "elements": len(elements)
            })
        
        self.current_screen_id = screen_id
        
        # Pick an action (BFS strategy)
        await self._pick_action(screen_id, elements)
    
    async def _pick_action(self, screen_id: str, elements: List[Dict]):
        """Choose and execute next action."""
        # Find untapped elements
        tapped = await db.fetchall(
            "SELECT id FROM elements WHERE screen_id = ? AND interacted = 1",
            (screen_id,)
        )
        tapped_ids = {e["id"] for e in tapped}
        
        # Get interactive elements
        interactive = [e for e in elements if e.get("type") in ["button", "link", "input", "clickable"]]
        
        for el in interactive:
            el_id = f"{screen_id}_el_{interactive.index(el)}"
            if el_id not in tapped_ids:
                # Execute tap
                x = int(el.get("x", 0)) + int(el.get("width", 0)) // 2
                y = int(el.get("y", 0)) + int(el.get("height", 0)) // 2
                
                success = await self.mcp.tap(x, y)
                
                if success:
                    # Mark as tapped
                    await db.execute(
                        "UPDATE elements SET interacted = 1, interaction_result = ? WHERE id = ?",
                        ("tapped", el_id)
                    )
                    
                    # Log transition
                    await db.execute(
                        """INSERT INTO transitions (from_screen_id, element_id, action_type, 
                           action_detail, timestamp) VALUES (?, ?, ?, ?, ?)""",
                        (screen_id, el_id, "tap", json.dumps({"x": x, "y": y}), time.time())
                    )
                    await db.commit()
                    
                    self.stats.actions_taken += 1
                    self._notify("action", {
                        "type": "tap",
                        "screen_id": screen_id,
                        "element": el.get("label", "unnamed")
                    })
                return
        
        # No untapped elements - go back
        await self.mcp.press_back()
        self._notify("action", {"type": "back", "screen_id": screen_id})
    
    def _stats_dict(self) -> Dict:
        return {
            "screens_found": self.stats.screens_found,
            "actions_taken": self.stats.actions_taken,
            "duration_seconds": self.stats.duration_seconds,
            "state": self.state.value
        }
    
    async def get_status(self) -> Dict:
        """Get current exploration status."""
        return {
            "state": self.state.value,
            "current_screen": self.current_screen_id,
            **self._stats_dict()
        }
