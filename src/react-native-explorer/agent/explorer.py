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

        # Limits
        self.max_screens = config.exploration.get("max_screens", 50)
        self.action_delay = config.exploration.get("action_delay_ms", 1500) / 1000.0
        
        # Statistics
        self.cache_hits = {"exact": 0, "similar": 0, "structure": 0}
        self.ai_calls = 0
        self.exploration_start_time = None

    async def start(self):
        """Initialize all components and start exploring in background."""
        console.print("[info]📡 Agent background task waiting for user...[/info]")
        
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
        """Main exploration loop for managed mode."""
        while self.running:
            # Check pause state
            if not self.pause_event.is_set():
                print("[EXPLORER] Paused")
                await self.pause_event.wait()
                if not self.running:
                    break
                print("[EXPLORER] Resumed")
            
            screen_count = await self.graph.get_screen_count()
            
            # Check screen limit
            if screen_count >= self.max_screens:
                print(f"[EXPLORER] Reached screen limit ({self.max_screens})")
                break
            
            current_transition_count = await self.graph.get_transition_count()
            
            # 🔧 Fixed: Always update UI status at the start of the loop
            await self.server.update_status(
                state="exploring",
                total_screens=screen_count,
                total_transitions=current_transition_count,
                total_actions=self.total_actions,
                message=f"Exploring... ({screen_count}/{self.max_screens} screens)"
            )
            
            print(f"[EXPLORER] Exploring... ({screen_count}/{self.max_screens} screens)")
            
            # 1. Capture current state
            screenshot = await self.mcp.take_screenshot()
            if not screenshot:
                logger.warning("Failed to capture screenshot, retrying...")
                await self.server.update_status(message="⚠️ Screenshot failed, retrying...")
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
                    print(f"[EXPLORER] Cache hit ({match_type}): Screen '{screen_data['name']}' already mapped")
                    self.current_screen_id = screen_id
                    await self._record_navigation_if_needed(screen_id, screen_data['name'])
                    await self._execute_strategy_on_screen_managed(screen_id)
                    continue
            
            # 4. AI Vision Analysis (only for truly new screens)
            print("[EXPLORER] Analyzing screen with AI...")
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
            
            print(f"[EXPLORER] New screen discovered: {screen_name} ({screen_type})")
            
            # 🔧 Notify UI
            await self.server.update_status(
                current_screen=screen_name,
                total_screens=await self.graph.get_screen_count(),
                total_actions=self.total_actions,
                message=f"New screen found: {screen_name}",
            )
            
            # 6. Execute strategy on this screen
            await self._execute_strategy_on_screen_managed(screen_id)
    
    async def _execute_strategy_on_screen_managed(self, screen_id: str):
        """Execute exploration strategy on current screen for managed mode."""
        strategy_name = self.config.exploration.get("strategy", "bfs")
        
        if strategy_name == "bfs":
            await self._bfs_explore_managed()
        elif strategy_name == "random":
            await self._random_explore_managed()
        else:
            await self._bfs_explore_managed()
    
    async def _bfs_explore_managed(self):
        """BFS exploration for managed mode."""
        # Get untried elements on current screen
        actions = await self.graph.get_untried_actions(self.current_screen_id)
        
        if not actions:
            print("[EXPLORER] No untried actions on this screen, going back...")
            await self._try_go_back()
            return
        
        # Try first untried action
        action = actions[0]
        await self._execute_action_managed(action)
    
    async def _random_explore_managed(self):
        """Random exploration for managed mode."""
        # Get all interactive elements
        elements = await self.graph.get_screen_elements(self.current_screen_id)
        
        if not elements:
            print("[EXPLORER] No interactive elements, going back...")
            await self._try_go_back()
            return
        
        # Pick random element
        import random
        element = random.choice(elements)
        
        action = {
            "element_id": element["id"],
            "action_type": "tap",
            "reason": "Random exploration",
        }
        await self._execute_action_managed(action)
    
    async def _execute_action_managed(self, action: dict):
        """Execute a single action for managed mode."""
        # Fix: DB uses 'id', but some code might expect 'element_id'
        element_id = action.get("id") or action.get("element_id")
        action_type = action.get("action_type", "tap")
        
        self.total_actions += 1
        
        print(f"[EXPLORER] Action #{self.total_actions}: {action_type} on element {element_id}")
        
        try:
            # Mark action as tried (Fix: Alias takes element_id and result, screen_id not needed)
            if element_id:
                await self.graph.mark_action_tried(element_id)
            
            # Execute via MCP
            success = await self.mcp.execute_action(action)
            
            if success:
                # Record transition
                action_detail = json.dumps(action) if isinstance(action, dict) else str(action)
                await self.graph.add_transition(
                    from_screen_id=self.current_screen_id,
                    to_screen_id=None,  # Will be updated when we discover the new screen
                    action_type=action_type,
                    element_id=element_id,
                    action_detail=action_detail,
                )
                
                # Wait for screen to settle
                await asyncio.sleep(self.action_delay)
            else:
                print(f"[EXPLORER] Action failed")
                
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            print(f"[ERROR] Action execution error: {e}")
    
    async def _try_go_back(self):
        """Try to navigate back."""
        try:
            await self.mcp.press_back()
            await asyncio.sleep(self.action_delay)
        except Exception as e:
            print(f"[EXPLORER] Go back failed: {e}")
    
    async def _finish_managed(self):
        """Cleanup for managed mode."""
        duration = time.time() - (self.exploration_start_time or time.time())
        try:
            screen_count = await self.graph.get_screen_count() if self.graph else 0
            print(f"[EXPLORER] Exploration complete! {screen_count} screens found in {duration:.1f}s")
            
            if self.server:
                await self.server.update_status(
                    state="idle",
                    message=f"🏁 Exploration complete: {screen_count} screens found",
                    total_screens=screen_count
                )
        except Exception:
            # Silently ignore errors during shutdown counters
            pass
            
        # Ensure MCP is disconnected
        try:
            if self.mcp:
                await self.mcp.disconnect()
        except Exception:
            pass
        await self.graph.close()
        await self.screen_cache.close()

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

        # Record transition from previous screen
        if self.current_screen_id and self.current_screen_id != screen_id:
            await self.graph.add_transition(
                from_screen_id=self.current_screen_id,
                to_screen_id=screen_id,
                action_type="navigate",
                action_detail=f"Discovered: {name}",
            )
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
