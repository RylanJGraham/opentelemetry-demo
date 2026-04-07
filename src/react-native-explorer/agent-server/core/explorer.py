"""Exploration engine - systematic BFS-based exploration."""
import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Set
from dataclasses import dataclass
from enum import Enum

from core.database import db
from core.utils import ImageHasher
from core.vision import VisionAnalyzer
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
class ExplorationConfig:
    """Configuration for exploration."""
    max_screens: int = 20
    max_depth: int = 15
    action_delay_ms: int = 3000
    max_duration_seconds: float = 900
    use_ai_vision: bool = True


@dataclass
class ScreenInfo:
    """Info about a discovered screen."""
    id: str
    name: str
    screen_type: str
    elements: List[Dict]
    tapped_elements: Set[int]  # Element indices already tapped
    visited_count: int = 0


class ExplorationEngine:
    """Systematic exploration using BFS strategy."""
    
    def __init__(self, config: ExplorationConfig, vision_analyzer: Optional[VisionAnalyzer] = None):
        self.config = config
        self.mcp = MCPClient()
        self.vision = vision_analyzer
        
        self.state = ExplorationState.IDLE
        self.current_screen_id: Optional[str] = None
        
        # Screen tracking using element structure hash (not screenshot hash)
        self._known_screens: Dict[str, ScreenInfo] = {}  # structure_hash -> ScreenInfo
        
        # Navigation for backtracking
        self._navigation_stack: List[str] = []  # Stack of screen structure hashes
        
        self._task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_event = asyncio.Event()
        self._callbacks: List[Callable] = []
        
        # Stats
        self._screens_found = 0
        self._actions_taken = 0
        self._start_time: Optional[float] = None
    
    def on_state_change(self, callback: Callable):
        self._callbacks.append(callback)
    
    def _notify(self, event: str, data: Any = None):
        for cb in self._callbacks:
            try:
                asyncio.create_task(cb(event, data))
            except Exception:
                pass
    
    async def start(self):
        if self.state == ExplorationState.EXPLORING:
            return {"status": "already_running"}
        
        self.state = ExplorationState.CONNECTING
        self._notify("state_change", {"state": self.state.value})
        
        connected = await self.mcp.connect()
        if not connected:
            self.state = ExplorationState.ERROR
            return {"status": "error", "message": "MCP connection failed"}
        
        # Reset state
        self._known_screens = {}
        self._navigation_stack = []
        self._screens_found = 0
        self._actions_taken = 0
        self._start_time = time.time()
        
        self.state = ExplorationState.EXPLORING
        self._stop_event.clear()
        self._pause_event.set()
        self._task = asyncio.create_task(self._exploration_loop())
        
        self._notify("state_change", {"state": self.state.value})
        return {"status": "started"}
    
    async def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.mcp.disconnect()
        self.state = ExplorationState.IDLE
        self._notify("state_change", {"state": self.state.value})
        return {"status": "stopped"}
    
    async def _exploration_loop(self):
        try:
            consecutive_errors = 0
            
            while not self._stop_event.is_set():
                if not self._pause_event.is_set():
                    await self._pause_event.wait()
                    if self._stop_event.is_set():
                        break
                
                # Check limits
                if self._screens_found >= self.config.max_screens:
                    logger.info(f"Reached max screens: {self.config.max_screens}")
                    break
                if time.time() - self._start_time > self.config.max_duration_seconds:
                    logger.info("Reached time limit")
                    break
                
                try:
                    success = await self._explore_step()
                    if success:
                        consecutive_errors = 0
                    else:
                        consecutive_errors += 1
                        if consecutive_errors >= 5:
                            logger.warning("Too many errors, stopping")
                            break
                except Exception as e:
                    logger.exception("Exploration step error")
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        break
                
                await asyncio.sleep(self.config.action_delay_ms / 1000)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Exploration error")
            self.state = ExplorationState.ERROR
        finally:
            if self.state != ExplorationState.ERROR:
                self.state = ExplorationState.COMPLETE
            self._notify("exploration_complete", {"stats": self._get_stats()})
    
    def _get_structure_hash(self, elements: List[Dict]) -> str:
        """Create a hash based on the structure of elements (not screenshot pixels)."""
        # Hash based on element types and their relative positions
        # This is more stable than screenshot hash (which changes with content)
        structure_parts = []
        for el in elements[:20]:  # Top 20 elements
            el_type = el.get('type', 'unknown')[:20]
            x = el.get('x', 0) // 50  # Bucket positions (50px buckets)
            y = el.get('y', 0) // 50
            w = el.get('width', 0) // 50
            h = el.get('height', 0) // 50
            structure_parts.append(f"{el_type}:{x}:{y}:{w}:{h}")
        
        import hashlib
        structure_str = "|".join(structure_parts)
        return hashlib.md5(structure_str.encode()).hexdigest()[:16]
    
    def _find_interactive_elements(self, elements: List[Dict]) -> List[int]:
        """Find indices of truly interactive elements (buttons, inputs, etc)."""
        interactive = []
        
        for i, el in enumerate(elements):
            el_type = el.get('type', '').lower()
            label = (el.get('label', '') or el.get('text', '')).lower()
            clickable = el.get('clickable', False)
            
            x = el.get('x', 0)
            y = el.get('y', 0)
            w = el.get('width', 0)
            h = el.get('height', 0)
            
            # STRICT: Only include known interactive types OR explicitly clickable
            interactive_types = {
                'button', 'imagebutton', 'switch', 'checkbox', 'radiobutton',
                'togglebutton', 'floatingactionbutton',
                'edittext', 'autocompletetextview', 'textinput',
                'spinner', 'dropdown', 'picker',
            }
            
            is_interactive_type = any(t in el_type for t in interactive_types)
            
            # Action keywords in label
            action_keywords = ['add', 'buy', 'cart', 'checkout', 'submit', 'save',
                             'edit', 'delete', 'back', 'next', 'continue', 'pay',
                             'order', 'search', 'menu', 'close', 'confirm', 'cancel']
            has_action_label = any(kw in label for kw in action_keywords)
            
            # Must be explicitly clickable OR interactive type
            is_interactive = (clickable is True) or (is_interactive_type and has_action_label)
            
            # Size and position checks
            valid_size = w >= 50 and h >= 40
            valid_position = y > 100 and y < 2200 and x > 10
            
            # NAVBAR BACK BUTTON DETECTION
            # Back buttons are typically:
            # - Small square icons (40-70px) in top-left area
            # - ImageView or View types
            # - y between 100-250 (below status bar, in header)
            # - x between 0-150 (left side)
            is_navbar_back = (
                40 <= w <= 100 and 40 <= h <= 100 and  # Small square-ish
                100 <= y <= 250 and 0 <= x <= 150 and   # Top-left area
                (el_type in ['imageview', 'view', 'image'] or 'button' in el_type)
            )
            
            if (is_interactive or is_navbar_back) and valid_size and valid_position:
                interactive.append(i)
                if is_navbar_back:
                    logger.debug(f"Found navbar back button: {el_type} at ({x},{y})")
        
        return interactive
    
    async def _explore_step(self) -> bool:
        """One exploration step: discover screen, decide action, execute."""
        # Take screenshot
        screenshot = await self.mcp.take_screenshot()
        if not screenshot:
            return False
        
        # Get elements from screen
        elements = await self.mcp.list_elements()
        
        # Use STRUCTURE hash for screen identity (not screenshot hash)
        structure_hash = self._get_structure_hash(elements)
        self.current_screen_id = structure_hash
        
        # Check if we've seen this screen structure before
        is_new_screen = structure_hash not in self._known_screens
        
        if is_new_screen:
            # This is a new screen - analyze it
            logger.info(f"New screen detected (structure: {structure_hash[:8]})")
            
            # Find interactive elements on this new screen
            interactive_indices = self._find_interactive_elements(elements)
            
            # Get AI name for this screen
            screen_name = "Unknown Screen"
            screen_type = "unknown"
            
            if self.vision and self.config.use_ai_vision:
                try:
                    analysis = await self.vision.analyze_screen(
                        screenshot, structure_hash, elements
                    )
                    screen_name = analysis.name
                    screen_type = analysis.screen_type
                except Exception as e:
                    logger.warning(f"AI analysis failed: {e}")
            
            # Save screenshot
            screenshot_path = f"screen_{structure_hash}.png"
            screenshot_dir = Path("./storage/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            (screenshot_dir / screenshot_path).write_bytes(screenshot)
            
            # Create screen info
            screen_info = ScreenInfo(
                id=structure_hash,
                name=screen_name,
                screen_type=screen_type,
                elements=elements,
                tapped_elements=set(),
                visited_count=1
            )
            self._known_screens[structure_hash] = screen_info
            
            # Save to DB
            content_hash = ImageHasher.content_hash(screenshot)
            await self._save_screen_to_db(structure_hash, screen_name, screen_type,
                                          elements, screenshot_path, content_hash)
            
            self._screens_found += 1
            self._notify("new_screen", {
                "id": structure_hash,
                "name": screen_name,
                "type": screen_type,
                "elements": len(elements),
                "interactive": len(interactive_indices)
            })
            
            logger.info(f"New screen: {screen_name} ({len(interactive_indices)} interactive)")
        else:
            # Known screen - increment visit count
            self._known_screens[structure_hash].visited_count += 1
            await db.update_screen_visit(structure_hash)
            self._notify("screen_visited", {"id": structure_hash})
            interactive_indices = self._find_interactive_elements(elements)
        
        # Get current screen info
        screen_info = self._known_screens[structure_hash]
        
        # Find untapped interactive elements
        untapped = [idx for idx in interactive_indices if idx not in screen_info.tapped_elements]
        
        if untapped:
            # Tap the first untapped element
            element_idx = untapped[0]
            element = elements[element_idx]
            
            x = element.get('x', 0) + element.get('width', 0) // 2
            y = element.get('y', 0) + element.get('height', 0) // 2
            label = element.get('label', '') or element.get('text', '')
            
            logger.info(f"Tapping element {element_idx}: {label[:30] or 'unnamed'} at ({x}, {y})")
            
            # Record transition before tap
            await db.record_transition(
                from_screen_id=structure_hash,
                to_screen_id=None,  # Will be updated when we see the new screen
                element_id=f"{structure_hash}_el_{element_idx}",
                action_type="tap",
                action_detail={"x": x, "y": y, "label": label}
            )
            
            # Mark as tapped
            screen_info.tapped_elements.add(element_idx)
            
            # Execute tap
            success = await self.mcp.tap(x, y)
            if success:
                self._actions_taken += 1
                self._navigation_stack.append(structure_hash)
                await asyncio.sleep(1.5)  # Wait for navigation
            
            return success
        else:
            # No more elements to tap on this screen - go back
            logger.info(f"No more elements on {screen_info.name}, going back")
            if self._navigation_stack:
                self._navigation_stack.pop()
                await self.mcp.press_back()
                await asyncio.sleep(1.5)
                return True
            else:
                logger.info("Nothing left to explore")
                return False
    
    async def _save_screen_to_db(self, screen_id: str, name: str, screen_type: str,
                                  elements: List[Dict], screenshot_path: str, 
                                  content_hash: str):
        """Save screen and elements to database."""
        try:
            # Save screen
            await db.execute(
                """INSERT INTO screens 
                   (id, name, screen_type, screenshot_path,
                    content_hash, element_count, first_seen, last_seen, fully_explored)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (screen_id, name, screen_type, screenshot_path,
                 content_hash, len(elements), time.time(), time.time(), 0)
            )
            
            # Save elements
            for i, el in enumerate(elements):
                await db.execute(
                    """INSERT INTO elements 
                       (id, screen_id, element_type, label, text_content,
                        x, y, width, height, clickable)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"{screen_id}_el_{i}",
                        screen_id,
                        el.get('type', 'unknown'),
                        el.get('label', '')[:100],
                        el.get('text', '')[:200],
                        el.get('x', 0),
                        el.get('y', 0),
                        el.get('width', 0),
                        el.get('height', 0),
                        1 if el.get('clickable', False) else 0
                    )
                )
            
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save screen to DB: {e}")
    
    def _get_stats(self) -> Dict:
        vision_stats = self.vision.get_stats() if self.vision else {}
        return {
            "screens_found": self._screens_found,
            "actions_taken": self._actions_taken,
            "duration_seconds": time.time() - self._start_time if self._start_time else 0,
            "state": self.state.value,
            "ai_api_calls": vision_stats.get('requests', 0),
        }
    
    async def get_status(self) -> Dict:
        return {
            "state": self.state.value,
            "current_screen": self.current_screen_id,
            **self._get_stats()
        }
