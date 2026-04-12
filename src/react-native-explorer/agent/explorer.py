"""
Enhanced exploration loop for the React Native Explorer Agent.
Implements intelligent sweep with multi-level caching and optimized AI usage.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List

# Force UTF-8 output on Windows to prevent emoji/unicode crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .graph import ScreenGraph
from .mcp_client import MobileMCPClient
from .server import ExplorerServer
from .strategy import ExplorationStrategy
from .utils import (
    Config,
    console,
    generate_screen_id,
    load_exploration_state,
    save_exploration_state,
    save_screenshot,
    setup_logging,
    ScreenCache,
    compute_content_hash,
    compute_phash,
    compute_structure_hash,
    fast_compare_screenshots,
)
from .vision import VisionAnalyzer

logger = logging.getLogger("explorer")


class Explorer:
    """
    Intelligent exploration agent with multi-level caching:
    1. Exact content hash match (instant, no AI)
    2. Perceptual hash match (similar appearance, no AI)
    3. Structure hash match (same layout, no AI)
    4. AI vision analysis (only for truly new screens)
    """

    def __init__(self, config: Config, resume: bool = False, graph: Optional[ScreenGraph] = None):
        print("[EXPLORER] Explorer.__init__ starting...", flush=True)
        self.config = config
        self.resume = resume

        # Components
        print("[EXPLORER] Creating MCP client...", flush=True)
        self.mcp = MobileMCPClient()
        print("[EXPLORER] Creating vision analyzer...", flush=True)
        self.vision = VisionAnalyzer(config)
        
        print("[EXPLORER] Initializing graph...", flush=True)
        # 🔧 Fix: Use injected graph if provided to avoid double-opening the DB file
        self.graph = graph or ScreenGraph(config.storage.get("database", "./storage/graph.db"))
        
        print("[EXPLORER] Creating strategy...", flush=True)
        self.strategy = ExplorationStrategy(config.exploration)
        
        print("[EXPLORER] Creating server...", flush=True)
        self.server = ExplorerServer(config, self.graph)
        self.server.explorer = self  # Link back for API control
        print("[EXPLORER] Explorer.__init__ complete", flush=True)

        # Lifecycle control (Event is set() when running, clear() when paused)
        self.pause_event = asyncio.Event()
        self.pause_event.clear()  # Start in paused state
        self.paused = True
        self.running = False
        self._stop_event = asyncio.Event()
        
        # Smart caching
        cache_dir = Path(config.storage.get("cache_dir", "./storage/cache"))
        self.screen_cache = ScreenCache(cache_dir)

        # Paths
        self.screenshots_dir = Path(config.storage.get("screenshots_dir", "./storage/screenshots"))
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = Path(config.storage.get("state_file", "./storage/exploration_state.json"))

        # State
        self.current_screen_id: Optional[str] = None
        self.current_screenshot: Optional[bytes] = None
        self.current_elements: List[dict] = []
        self.total_actions = 0
        self._last_transition_id: Optional[int] = None  # Track pending transition for to_screen_id update

        # Limits
        self.max_screens = config.exploration.get("max_screens", 50)
        self.action_delay = config.exploration.get("action_delay_ms", 1500) / 1000.0
        
        # Statistics
        self.cache_hits = {"exact": 0, "similar": 0, "structure": 0}
        self.ai_calls = 0
        self.exploration_start_time = None

    async def start(self):
        """Initialize all components and start exploring in background."""
        print("[EXPLORER] Agent ready — waiting for Play signal from UI...")
        
        # 🔧 Fix: Wait for the UI 'Play' command BEFORE doing heavy lifting
        await self.pause_event.wait()
        
        # Connect to MCP / Android emulator
        await self.server.update_status(state="connecting", message="Connecting to Android emulator...")
        try:
            tools = await self.mcp.connect()
            console.print(f"[success]✅ Connected to emulator with {len(tools)} tools[/success]")
        except Exception as e:
            console.print(f"[error]❌ Failed to connect to emulator: {e}[/error]")
            console.print("[warning]Make sure an Android emulator is running (adb devices)[/warning]")
            await self.cleanup()
            return

        # Auto-launch the target app if configured
        package_name = self.config.app.get("package_name", "")
        if package_name:
            console.print(f"[info]🚀 Launching app: {package_name}[/info]")
            await self.mcp.launch_app(package_name)
            await asyncio.sleep(2)  # Wait for app to launch

        # Load resume state if applicable
        if self.resume:
            state = load_exploration_state(self.state_file)
            if state:
                self.current_screen_id = state.get("current_screen_id")
                self.total_actions = state.get("total_actions", 0)
                console.print(f"[info]📂 Resumed from action #{self.total_actions}[/info]")

        # Start exploration loop
        self.running = True
        self.exploration_start_time = time.time()
        await self.server.update_status(state="exploring", message="Exploration started!")

        try:
            await self._exploration_loop()
        except KeyboardInterrupt:
            console.print("\n[warning]⚠️  Exploration interrupted by user[/warning]")
        except Exception as e:
            logger.exception(f"Exploration error: {e}")
        finally:
            await self._finish()

    async def start_managed(self):
        """Run exploration in managed mode (no server, stdout communication)."""
        print("[EXPLORER] Initializing...")
        sys.stdout.flush()
        
        # Connect to graph DB (only if not already connected)
        if not self.graph._db:
            print("[EXPLORER] Connecting to database...")
            sys.stdout.flush()
            await self.graph.connect()
            print("[EXPLORER] Database connected")
            sys.stdout.flush()
        
        # Connect to MCP / Android emulator
        print("[EXPLORER] Connecting to Android emulator...")
        sys.stdout.flush()
        try:
            tools = await self.mcp.connect()
            print(f"[EXPLORER] Connected to emulator with {len(tools)} tools")
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Failed to connect to emulator: {e}")
            print("[ERROR] Make sure an Android emulator is running (adb devices)")
            sys.stdout.flush()
            await self.cleanup()
            return
        
        # Auto-launch the target app if configured
        package_name = self.config.app.get("package_name", "")
        if package_name:
            print(f"[EXPLORER] Launching app: {package_name}")
            sys.stdout.flush()
            await self.mcp.launch_app(package_name)
            await asyncio.sleep(2)  # Wait for app to launch
        
        # Load resume state if applicable
        if self.resume:
            state = load_exploration_state(self.state_file)
            if state:
                self.current_screen_id = state.get("current_screen_id")
                self.total_actions = state.get("total_actions", 0)
                print(f"[EXPLORER] Resumed from action #{self.total_actions}")
        
        # Start exploration loop
        self.running = True
        self.exploration_start_time = time.time()
        print("[EXPLORER] Exploration started!")
        
        try:
            await self._exploration_loop_managed()
        except KeyboardInterrupt:
            print("[EXPLORER] Exploration interrupted by user")
            await self.server.update_status(message="⏹ Stopped by user")
        except Exception as e:
            logger.exception(f"Exploration error: {e}")
            print(f"[ERROR] Exploration error: {e}")
            await self.server.update_status(state="error", message=f"❌ Error: {str(e)}")
        finally:
            await self._finish_managed()
    
    async def _exploration_loop_managed(self):
        """
        Main managed-mode exploration loop — two-level architecture.
        
        OUTER LOOP: capture → identify screen (cache or AI) → patch transition
        INNER LOOP: exhaust all interesting elements on the current screen,
                    breaking back to the outer loop only when the screen changes.
        """
        # Outer-loop stuck detection: how many consecutive iterations
        # identified the same screen with no new progress.
        outer_same_screen_count = 0
        outer_last_screen_id = None
        outer_last_element_count = 0  # track progress within a screen
        max_outer_stuck = 5  # after this many with no progress, back out
        
        while self.running:
            # ── Pause gate ────────────────────────────────────────
            if not self.pause_event.is_set():
                print("[EXPLORER] Paused — waiting for resume...")
                await self.server.update_status(state="paused", message="⏸ Paused")
                await self.pause_event.wait()
                if not self.running:
                    break
                print("[EXPLORER] Resumed")
            
            # ── Check limits ──────────────────────────────────────
            screen_count = await self.graph.get_screen_count()
            if screen_count >= self.max_screens:
                print(f"[EXPLORER] Reached screen limit ({self.max_screens})")
                await self.server.update_status(
                    state="complete",
                    message=f"🎉 Reached screen limit ({self.max_screens})",
                    total_screens=screen_count,
                )
                break
            
            transition_count = await self.graph.get_transition_count()
            await self.server.update_status(
                state="exploring",
                total_screens=screen_count,
                total_transitions=transition_count,
                total_actions=self.total_actions,
                message=f"Exploring... ({screen_count}/{self.max_screens} screens)",
            )
            
            # ── STEP 1: Capture current state ─────────────────────
            screenshot = await self.mcp.take_screenshot()
            if not screenshot:
                print("[EXPLORER] Screenshot failed, retrying...")
                await asyncio.sleep(2)
                continue
            
            self.current_screenshot = screenshot
            
            # Get accessibility tree for structure hashing
            elements_raw = await self.mcp.list_elements()
            self.current_elements = elements_raw or []
            accessibility_text = json.dumps(elements_raw, sort_keys=True) if elements_raw else ""
            
            # ── STEP 2: Identify screen (cache or AI) ─────────────
            screen_id = None
            screen_name = "Unknown"
            is_new_screen = False
            
            cache_result = await self._check_cache(screenshot, self.current_elements)
            
            if cache_result["hit"]:
                # CACHE HIT — no AI needed
                screen_id = cache_result["screen_id"]
                match_type = cache_result["match_type"]
                self.cache_hits[match_type] += 1
                
                screen_data = await self.graph.get_screen(screen_id)
                screen_name = screen_data["name"] if screen_data else "Cached"
                
                print(f"[EXPLORER] Cache hit ({match_type}): '{screen_name}'")
            else:
                # CACHE MISS — AI vision analysis
                print("[EXPLORER] New screen — analyzing with AI...")
                analysis = await self.vision.analyze_screen(screenshot, accessibility_text)
                self.ai_calls += 1
                
                screen_name = analysis.get("screen_name", "Unknown")
                screen_type = analysis.get("screen_type", "unknown")
                description = analysis.get("description", "")
                interactive_elements = analysis.get("interactive_elements", [])
                features = analysis.get("features", {})
                
                screen_id = await self._create_screen(
                    screenshot, screen_name, screen_type, description,
                    interactive_elements, features,
                )
                is_new_screen = True
                
                print(f"[EXPLORER] New screen: '{screen_name}' ({screen_type}) — {len(interactive_elements)} elements")
                
                await self.server.update_status(
                    current_screen=screen_name,
                    total_screens=await self.graph.get_screen_count(),
                    total_actions=self.total_actions,
                    message=f"New screen: {screen_name}",
                )
            
            # ── STEP 3: Patch the previous transition's target ────
            if self._last_transition_id:
                await self.graph.update_transition_target(self._last_transition_id, screen_id)
                self._last_transition_id = None
            
            self.current_screen_id = screen_id
            
            # ── STEP 4: Outer-loop stuck detection ────────────────
            unexplored_now = await self.graph.get_unexplored_elements(screen_id)
            
            if screen_id == outer_last_screen_id:
                # Same screen as last outer-loop iteration
                if len(unexplored_now) >= outer_last_element_count:
                    # No progress since last time (same or more unexplored)
                    outer_same_screen_count += 1
                else:
                    # We made progress (fewer unexplored elements)
                    outer_same_screen_count = 0
            else:
                # Different screen — reset stuck counter
                outer_same_screen_count = 0
            
            outer_last_screen_id = screen_id
            outer_last_element_count = len(unexplored_now)
            
            if outer_same_screen_count >= max_outer_stuck:
                print(f"[EXPLORER] Stuck on '{screen_name}' after {max_outer_stuck} outer iterations — backing out")
                await self.graph.mark_screen_explored(screen_id)
                await self._try_go_back()
                outer_same_screen_count = 0
                continue
            
            # ── STEP 5: INNER LOOP — exhaust elements on this screen ──
            await self._exhaust_screen_elements(screen_id, screen_name)
    
    async def _exhaust_screen_elements(self, screen_id: str, screen_name: str):
        """
        Inner exploration loop: interact with all unexplored elements on
        the current screen, one at a time. After each action:
          - Wait for UI to settle
          - Take a new screenshot and fast-compare to the pre-action screenshot
          - If the screen changed → break (outer loop will identify the new screen)
          - If the screen is the same → mark element interacted, continue
          
        When all elements are exhausted, mark the screen explored and go back.
        """
        max_actions_this_screen = self.config.exploration.get("max_actions_per_screen", 15)
        actions_this_screen = 0
        
        while self.running and actions_this_screen < max_actions_this_screen:
            # Check pause
            if not self.pause_event.is_set():
                return  # let outer loop handle pause
            
            # Get fresh list of unexplored elements
            unexplored = await self.graph.get_unexplored_elements(screen_id)
            
            if not unexplored:
                # All elements explored on this screen
                print(f"[EXPLORER] Screen '{screen_name}' fully explored ({actions_this_screen} actions)")
                await self.graph.mark_screen_explored(screen_id)
                
                # Check if there are any unexplored screens left
                all_screens = await self.graph.get_all_screens()
                unexplored_screens = [s for s in all_screens if not s.get("fully_explored")]
                if not unexplored_screens:
                    print("[EXPLORER] All reachable screens explored!")
                    self.running = False
                    return
                
                # Go back to try reaching other screens
                await self._try_go_back()
                return  # outer loop will capture the new screen
            
            # Pick the next element via strategy
            pick = self.strategy.pick_next_element(unexplored)
            if not pick:
                # Strategy says nothing worth trying — mark explored and back
                await self.graph.mark_screen_explored(screen_id)
                await self._try_go_back()
                return
            
            element = pick["element"]
            action_type = pick["action"]
            coords = pick["coordinates"]
            reason = pick["reason"]
            
            print(f"[EXPLORER] → {action_type.upper()}: {reason}")
            await self.server.update_status(
                current_screen=screen_name,
                total_actions=self.total_actions,
                message=f"{action_type.upper()}: {element.get('label', 'unknown')}",
            )
            
            # Snapshot before action (for change detection)
            pre_action_screenshot = self.current_screenshot
            
            # Execute the action
            self.total_actions += 1
            actions_this_screen += 1
            
            action_detail = json.dumps({
                "element_id": element.get("id", ""),
                "label": element.get("label", ""),
                "type": element.get("type", ""),
                "x": int(coords[0]) if coords else 0,
                "y": int(coords[1]) if coords else 0,
            }, default=str)
            
            success = False
            if action_type == "tap":
                success = await self.mcp.tap(int(coords[0]), int(coords[1]))
            elif action_type == "type":
                # Tap to focus, then type
                await self.mcp.tap(int(coords[0]), int(coords[1]))
                await asyncio.sleep(0.3)
                success = await self.mcp.type_text("test@example.com")
            
            if not success:
                # Action failed — mark element as interacted (to skip next time) and continue
                await self.graph.mark_element_interacted(element.get("id", ""), result="failed")
                continue
            
            # Record transition (to_screen_id=None, will be patched by outer loop)
            transition_id = await self.graph.add_transition(
                from_screen_id=screen_id,
                to_screen_id=None,
                action_type=action_type,
                element_id=element.get("id", ""),
                action_detail=action_detail,
            )
            self._last_transition_id = transition_id
            
            # Log the action
            await self.graph.log_action(
                action_type=action_type,
                screen_id=screen_id,
                element_id=element.get("id", ""),
                detail=reason,
            )
            
            # Mark element as interacted
            await self.graph.mark_element_interacted(
                element.get("id", ""),
                result=f"{action_type}ed at ({int(coords[0])},{int(coords[1])})",
            )
            
            # Wait for screen to settle
            await self._wait_for_screen_settle()
            
            # Take post-action screenshot and check if screen changed
            post_screenshot = await self.mcp.take_screenshot()
            if not post_screenshot:
                continue
            
            self.current_screenshot = post_screenshot
            
            if not fast_compare_screenshots(pre_action_screenshot, post_screenshot, threshold=0.92):
                # Screen changed! Break to outer loop to identify the new screen.
                print(f"[EXPLORER] Screen changed after {action_type} → '{element.get('label', '')}'")
                
                # Notify UI
                await self.server.notify_action({
                    "action": action_type,
                    "screen": screen_name,
                    "reason": f"Tapped {element.get('label', '')} — screen changed",
                    "element": element,
                    "timestamp": time.time(),
                })
                return  # outer loop will identify the new screen
            else:
                # Same screen — the transition target is self (navigation didn't happen)
                # Patch the transition to point back to the same screen
                await self.graph.update_transition_target(transition_id, screen_id)
                self._last_transition_id = None
                
                # Notify UI
                await self.server.notify_action({
                    "action": action_type,
                    "screen": screen_name,
                    "reason": f"Tapped {element.get('label', '')} — same screen",
                    "element": element,
                    "timestamp": time.time(),
                })
        
        # Max actions hit — mark explored and move on
        if actions_this_screen >= max_actions_this_screen:
            print(f"[EXPLORER] Max actions ({max_actions_this_screen}) on '{screen_name}' — moving on")
            await self.graph.mark_screen_explored(screen_id)
            await self._try_go_back()
    
    async def _try_go_back(self):
        """Navigate back, recording a 'back' transition in the graph."""
        try:
            # Record the back-press transition (to_screen_id=None, patched by outer loop next iteration)
            if self.current_screen_id:
                transition_id = await self.graph.add_transition(
                    from_screen_id=self.current_screen_id,
                    to_screen_id=None,
                    action_type="back",
                    action_detail=json.dumps({"reason": "backtracking"}),
                )
                self._last_transition_id = transition_id
            
            success = await self.mcp.press_back()
            if success:
                self.total_actions += 1
                await self._wait_for_screen_settle()
            else:
                print("[EXPLORER] Back press failed")
                self._last_transition_id = None
        except Exception as e:
            print(f"[EXPLORER] Go back failed: {e}")
            self._last_transition_id = None
    
    async def _wait_for_screen_settle(self, max_polls: int = 5, poll_interval: float = 0.4):
        """
        Smart screen settling: poll screenshots until the UI stops changing.
        
        Instead of a fixed delay, this takes up to `max_polls` screenshots at
        `poll_interval` intervals and compares consecutive ones. Once two
        consecutive screenshots are similar (>97%), the screen is considered settled.
        
        Worst-case time: max_polls * poll_interval = 2.0s
        """
        prev_screenshot = None
        for i in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                current = await self.mcp.take_screenshot()
                if current and prev_screenshot:
                    if fast_compare_screenshots(prev_screenshot, current, threshold=0.97):
                        return  # UI has settled
                prev_screenshot = current
            except Exception:
                await asyncio.sleep(self.action_delay)
                return
        # Max polls reached — proceed anyway

    async def _finish_managed(self):
        """Cleanup for managed mode."""
        duration = time.time() - (self.exploration_start_time or time.time())
        try:
            screen_count = await self.graph.get_screen_count() if self.graph else 0
            transition_count = await self.graph.get_transition_count() if self.graph else 0
            print(f"[EXPLORER] Exploration complete! {screen_count} screens, {transition_count} transitions in {duration:.1f}s")
            print(f"[EXPLORER] Cache hits: exact={self.cache_hits['exact']}, similar={self.cache_hits['similar']}, AI calls={self.ai_calls}")
            
            if self.server:
                await self.server.update_status(
                    state="idle",
                    message=f"🏁 Complete: {screen_count} screens, {transition_count} transitions",
                    total_screens=screen_count,
                    total_transitions=transition_count,
                    total_actions=self.total_actions,
                )
            
            # Auto-cluster screens at the end
            if self.graph:
                await self.graph.auto_cluster_screens()
        except Exception as e:
            print(f"[EXPLORER] Shutdown stats error (non-fatal): {e}")
            
        # Ensure MCP is disconnected
        try:
            if self.mcp:
                await self.mcp.disconnect()
        except Exception:
            pass
        
        try:
            await self.graph.close()
        except Exception:
            pass
        
        # ScreenCache is synchronous, no await needed
        try:
            self.screen_cache._save_index()
        except Exception:
            pass

    async def _exploration_loop(self):
        """Main exploration loop with smart caching."""
        while self.running:
            # Check pause state
            if not self.pause_event.is_set():
                await self.server.update_status(state="paused", message="Agent paused")
                await self.pause_event.wait()
                if not self.running:
                    break
                await self.server.update_status(state="exploring", message="Exploration resumed")

            screen_count = await self.graph.get_screen_count()

            # Check screen limit
            if screen_count >= self.max_screens:
                console.print(f"[success]🎉 Reached screen limit ({self.max_screens})[/success]")
                break

            # 1. Capture current state
            screenshot = await self.mcp.take_screenshot()
            if not screenshot:
                logger.warning("Failed to capture screenshot, retrying...")
                await asyncio.sleep(2)
                continue

            self.current_screenshot = screenshot

            # 2. Get accessibility tree
            elements_raw = await self.mcp.list_elements()
            self.current_elements = elements_raw if elements_raw else []
            accessibility_text = json.dumps(elements_raw, sort_keys=True) if elements_raw else ""

            # 3. Multi-level cache check
            cache_result = await self._check_cache(screenshot, self.current_elements)
            
            if cache_result["hit"]:
                # Cache hit! No AI needed
                screen_id = cache_result["screen_id"]
                match_type = cache_result["match_type"]
                self.cache_hits[match_type] += 1
                
                screen_data = await self.graph.get_screen(screen_id)
                if screen_data:
                    console.print(f"  [cache]♻️  Cache Hit ({match_type}):[/cache] Screen '{screen_data['name']}' already mapped.")
                    self.current_screen_id = screen_id
                    await self._record_navigation_if_needed(screen_id, screen_data['name'])
                    
                    await self.server.update_status(
                        current_screen=screen_data['name'],
                        total_screens=await self.graph.get_screen_count(),
                        total_actions=self.total_actions,
                        message=f"Cache hit ({match_type}): {screen_data['name']}",
                    )
                    await self._execute_strategy_on_screen(screen_id)
                    continue

            # 4. AI Vision Analysis (only for truly new screens)
            await self.server.update_status(message="Analyzing screen with AI...")
            analysis = await self.vision.analyze_screen(screenshot, accessibility_text)
            self.ai_calls += 1

            screen_name = analysis.get("screen_name", "Unknown")
            screen_type = analysis.get("screen_type", "unknown")
            description = analysis.get("description", "")
            interactive_elements = analysis.get("interactive_elements", [])
            features = analysis.get("features", {})

            # 5. Create new screen entry
            screen_id = await self._create_screen(
                screenshot, screen_name, screen_type, description,
                interactive_elements, features
            )
            self.current_screen_id = screen_id

            # 6. Execute strategy on this screen
            await self._execute_strategy_on_screen(screen_id)

    async def _check_cache(self, screenshot: bytes, elements: List[dict]) -> dict:
        """
        Check multi-level cache for screen match.
        Returns: {hit: bool, screen_id: str, match_type: str}
        """
        # Level 1: Exact content hash
        content_hash = compute_content_hash(screenshot)
        existing = await self.graph.get_screen_by_hash(content_hash)
        if existing:
            return {"hit": True, "screen_id": existing["id"], "match_type": "exact"}

        # Level 2: Perceptual hash (similar appearance)
        phash = compute_phash(screenshot)
        similar_screens = await self.graph.get_screens_by_phash(phash)
        if similar_screens:
            return {"hit": True, "screen_id": similar_screens[0]["id"], "match_type": "similar"}

        # Level 3: Structure hash (same layout)
        structure_hash = compute_structure_hash(elements)
        # This would need a structure hash index in the DB
        # For now, skip to AI analysis

        return {"hit": False, "screen_id": None, "match_type": None}

    async def _create_screen(
        self,
        screenshot: bytes,
        name: str,
        screen_type: str,
        description: str,
        interactive_elements: List[dict],
        features: dict,
    ) -> str:
        """Create a new screen entry with all metadata."""
        screen_id = generate_screen_id()

        # Compute hashes
        content_hash = compute_content_hash(screenshot)
        phash = compute_phash(screenshot)
        structure_hash = compute_structure_hash(self.current_elements)

        # Save screenshot
        screenshot_filename = f"{screen_id}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        save_screenshot(screenshot, screenshot_path)

        # Add to graph
        await self.graph.add_screen(
            screen_id=screen_id,
            name=name,
            screen_type=screen_type,
            description=description,
            screenshot_path=screenshot_filename,
            element_count=len(interactive_elements),
            phash=phash,
            content_hash=content_hash,
            structure_hash=structure_hash,
        )

        # Add screen features
        for feature_name, feature_value in features.items():
            if feature_value:
                await self.graph.add_screen_feature(
                    screen_id, feature_name, str(feature_value), confidence=1.0
                )

        # Add elements to graph
        for idx, el in enumerate(interactive_elements):
            element_id = f"{screen_id}_el_{idx}"
            await self.graph.add_element(
                element_id=element_id,
                screen_id=screen_id,
                element_type=el.get("type", "unknown"),
                label=el.get("label", ""),
                x=int(el.get("x", 0)),
                y=int(el.get("y", 0)),
                text_content=el.get("text_content", ""),
                accessibility_id=el.get("accessibility_id", ""),
                confidence=el.get("confidence", 1.0),
            )

        # Notify UI about the transition (the actual DB transition is handled by the outer loop)
        if self.current_screen_id and self.current_screen_id != screen_id:
            await self.server.notify_new_transition({
                "from": self.current_screen_id,
                "to": screen_id,
                "action": "navigate",
            })

        # Cache the screen
        self.screen_cache.add_screen(
            screen_id, screenshot, self.current_elements,
            {"name": name, "type": screen_type}
        )

        # Notify web UI
        screen_data = await self.graph.get_screen(screen_id)
        if screen_data:
            screen_data["elements"] = interactive_elements
            screen_data["features"] = features
            await self.server.notify_new_screen(screen_data)

        console.print(
            f"  [success]📱 New screen:[/success] {name} ({screen_type}) "
            f"— {len(interactive_elements)} elements"
        )

        return screen_id

    async def _execute_strategy_on_screen(self, screen_id: str):
        """Helper to decide and run next action for a given screen."""
        screen_data = await self.graph.get_screen(screen_id)
        screen_name = screen_data.get("name", "Unknown") if screen_data else "Unknown"
        screen_type = screen_data.get("screen_type", "unknown") if screen_data else "unknown"

        # Update status
        await self.server.update_status(
            current_screen=screen_name,
            total_screens=await self.graph.get_screen_count(),
            total_actions=self.total_actions,
            message=f"On screen: {screen_name}",
        )

        # Get unexplored elements for this screen
        unexplored = await self.graph.get_unexplored_elements(screen_id)
        all_elements = await self.graph.get_elements_for_screen(screen_id)
        is_fully_explored = screen_data.get("fully_explored", False) if screen_data else False
        transitions = await self.graph.get_transitions_from(screen_id)

        # Decide next action
        decision = self.strategy.decide_next_action(
            screen_id, unexplored, all_elements, is_fully_explored, screen_type, transitions
        )

        action = decision["action"]
        element = decision.get("element")
        reason = decision.get("reason", "")

        console.print(f"  [explore]→ {action.upper()}[/explore]: {reason}")

        # Notify web UI
        await self.server.notify_action({
            "action": action,
            "screen": screen_name,
            "reason": reason,
            "element": element,
            "timestamp": time.time(),
        })

        # Execute action
        await self._execute_action(action, element, decision, screen_id)

    async def _execute_action(self, action: str, element: dict, decision: dict, screen_id: str):
        """Execute the chosen exploration action."""
        if action == "done":
            # Try to find another unexplored screen
            all_screens = await self.graph.get_all_screens()
            has_unexplored = any(not s["fully_explored"] for s in all_screens)
            if not has_unexplored:
                console.print("[success]🎉 All reachable screens explored![/success]")
                self.running = False
                return
            else:
                await self.graph.mark_screen_explored(screen_id)
                return

        elif action == "tap" and element:
            coords = decision.get("coordinates", (0, 0))
            await self.graph.mark_element_interacted(
                element.get("id", ""), result=f"tapped"
            )

            success = await self.mcp.tap(int(coords[0]), int(coords[1]))
            if success:
                self.total_actions += 1
                await asyncio.sleep(self.action_delay)

        elif action == "back":
            success = await self.mcp.press_back()
            if success:
                self.total_actions += 1
                await asyncio.sleep(self.action_delay)

        elif action == "swipe":
            swipe_data = decision.get("swipe", {})
            if swipe_data:
                await self.mcp.swipe(
                    swipe_data.get("x1", 540),
                    swipe_data.get("y1", 1500),
                    swipe_data.get("x2", 540),
                    swipe_data.get("y2", 500),
                )
                self.total_actions += 1
                await asyncio.sleep(self.action_delay)

        elif action == "type" and element:
            await self.mcp.tap(int(element.get("x", 0)), int(element.get("y", 0)))
            await asyncio.sleep(0.5)
            await self.mcp.type_text("test@example.com")
            await self.graph.mark_element_interacted(
                element.get("id", ""), result="typed test text"
            )
            self.total_actions += 1
            await asyncio.sleep(self.action_delay)

        # Log action
        await self.graph.log_action(
            action_type=action,
            screen_id=screen_id,
            element_id=element.get("id", "") if element else "",
            detail=decision.get("reason", ""),
        )

    async def _record_navigation_if_needed(self, screen_id: str, screen_name: str):
        """Record transition from previous screen if it represents navigation."""
        if self.current_screen_id and self.current_screen_id != screen_id:
            await self.graph.add_transition(
                from_screen_id=self.current_screen_id,
                to_screen_id=screen_id,
                action_type="navigate",
                action_detail=f"Navigated to: {screen_name}",
            )
            await self.server.notify_new_transition({
                "from": self.current_screen_id,
                "to": screen_id,
                "action": "navigate",
            })

    async def _finish(self):
        """Finish exploration and print summary."""
        duration = time.time() - self.exploration_start_time if self.exploration_start_time else 0
        
        console.print("\n[bold cyan]═══ Exploration Complete ═══[/bold cyan]")

        screen_count = await self.graph.get_screen_count()
        transitions = await self.graph.get_all_transitions()
        vision_stats = self.vision.stats
        strategy_stats = self.strategy.stats
        cache_stats = self.screen_cache.get_stats()

        console.print(f"  📱 Screens discovered:  {screen_count}")
        console.print(f"  🔗 Transitions:         {len(transitions)}")
        console.print(f"  👆 Total actions:        {self.total_actions}")
        console.print(f"  ⏱️  Duration:             {duration:.1f}s")
        console.print(f"\n  [cache]Cache Performance:[/cache]")
        console.print(f"     Exact matches:       {self.cache_hits['exact']}")
        console.print(f"     Similar matches:     {self.cache_hits['similar']}")
        console.print(f"     AI API calls:        {self.ai_calls}")
        console.print(f"\n  [ai]AI Usage:[/ai]")
        console.print(f"     Total tokens:        {vision_stats['input_tokens'] + vision_stats['output_tokens']}")
        console.print(f"     Estimated cost:      ${vision_stats['estimated_cost_usd']:.4f}")
        console.print()

        # Auto-cluster screens
        await self.graph.auto_cluster_screens()
        clusters = await self.graph.get_clusters()
        console.print(f"  [success]Auto-clustered into {len(clusters)} groups[/success]")

        await self.server.update_status(
            state="complete",
            total_screens=screen_count,
            total_actions=self.total_actions,
            message=f"Exploration complete! {screen_count} screens found.",
            stats={
                "duration_seconds": duration,
                "cache_hits": self.cache_hits,
                "ai_calls": self.ai_calls,
                "ai_cost_usd": vision_stats['estimated_cost_usd'],
            }
        )

        # Keep server running for UI
        console.print(
            f"[info]🌐 Web UI still running at http://localhost:{self.config.ui.get('port', 3000)}[/info]"
        )
        console.print("[info]   Press Ctrl+C to stop[/info]\n")

        await self.cleanup(keep_server=True)

        # Save final state
        save_exploration_state({
            "current_screen_id": self.current_screen_id,
            "total_actions": self.total_actions,
            "screens_found": screen_count,
            "cache_hits": self.cache_hits,
            "ai_calls": self.ai_calls,
        }, self.state_file)

        # Wait for Ctrl+C
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await self.server.stop()

    async def cleanup(self, keep_server: bool = False):
        """Clean up all resources."""
        await self.mcp.disconnect()
        await self.vision.close()
        if not keep_server:
            await self.server.stop()
            await self.graph.close()

    # ── Public API for server integration ─────────────────────────────

    async def create_story_from_path(self, screen_path: List[str], name: str) -> str:
        """
        Create a user story from a path of screens.
        
        Args:
            screen_path: List of screen IDs representing a user journey
            name: Name for the story
        
        Returns:
            story_id
        """
        from .utils import generate_story_id
        
        story_id = generate_story_id()
        await self.graph.create_story(
            story_id=story_id,
            name=name,
            description=f"Auto-generated from exploration path",
            tags=["auto", "exploration"],
        )

        # Create steps from path
        for i, screen_id in enumerate(screen_path):
            screen = await self.graph.get_screen(screen_id)
            if screen:
                await self.graph.add_story_step(
                    story_id=story_id,
                    step_number=i + 1,
                    action_type="navigate" if i > 0 else "start",
                    screen_id=screen_id,
                    data={"screen_name": screen["name"]},
                )

        return story_id

    async def generate_story_from_flow(self, start_screen: str, end_screen: str, name: str) -> Optional[str]:
        """
        Auto-generate a story representing the shortest path between two screens.
        
        Returns:
            story_id or None if no path found
        """
        path = await self.graph.get_shortest_path(start_screen, end_screen)
        if not path:
            return None
        
        return await self.create_story_from_path(path, name)


# Keep main() and CLI entry point unchanged
# ... [previous main() code] ...
