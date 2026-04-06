"""
Main exploration loop for the React Native Explorer Agent.
Connects all components: MCP client, vision analyzer, screen graph, and strategy engine.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from .graph import ScreenGraph
from .mcp_client import MobileMCPClient
from .server import ExplorerServer
from .strategy import ExplorationStrategy
from .utils import (
    Config,
    console,
    generate_screen_id,
    load_exploration_state,
    resize_screenshot,
    save_exploration_state,
    save_screenshot,
    setup_logging,
)
from .vision import VisionAnalyzer

logger = logging.getLogger("explorer")


class Explorer:
    """
    Main exploration agent. Orchestrates:
    1. MCP connection to the Android emulator
    2. Vision-based screen analysis
    3. Graph construction
    4. Strategy-driven action selection
    5. Real-time web UI updates
    """

    def __init__(self, config: Config, resume: bool = False):
        self.config = config
        self.resume = resume

        # Components
        self.mcp = MobileMCPClient()
        self.vision = VisionAnalyzer(config)
        self.graph = ScreenGraph(config.storage.get("database", "./storage/graph.db"))
        self.strategy = ExplorationStrategy(config.exploration)
        self.server = ExplorerServer(config, self.graph)

        # State
        self.screenshots_dir = Path(config.storage.get("screenshots_dir", "./storage/screenshots"))
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = Path(config.storage.get("state_file", "./storage/exploration_state.json"))

        self.current_screen_id: Optional[str] = None
        self.current_screenshot: Optional[bytes] = None
        self._previous_screenshots: dict[str, bytes] = {}  # screen_id -> screenshot bytes
        self.total_actions = 0
        self.running = False

        # Limits
        self.max_screens = config.exploration.get("max_screens", 20)
        self.action_delay = config.exploration.get("action_delay_ms", 1500) / 1000.0

    async def start(self):
        """Initialize all components and start exploring."""
        console.print("\n[bold cyan]🚀 React Native Explorer Agent[/bold cyan]")
        console.print(f"   Max screens: {self.max_screens}")
        console.print(f"   Vision model: {self.config.vision.get('model')}")
        console.print(f"   Action delay: {self.action_delay}s\n")

        # Start API server
        await self.server.start()
        await self.server.update_status(state="initializing", message="Starting up...")

        # Connect to graph DB
        await self.graph.connect()

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
        await self.server.update_status(state="exploring", message="Exploration started!")

        try:
            await self._exploration_loop()
        except KeyboardInterrupt:
            console.print("\n[warning]⚠️  Exploration interrupted by user[/warning]")
        except Exception as e:
            logger.exception(f"Exploration error: {e}")
        finally:
            await self._finish()

    async def _exploration_loop(self):
        """Main exploration loop."""
        while self.running:
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
            accessibility_text = json.dumps(elements_raw, indent=2) if elements_raw else ""

            # 3. Analyze screen with vision
            await self.server.update_status(message="Analyzing screen...")
            analysis = await self.vision.analyze_screen(screenshot, accessibility_text)

            screen_name = analysis.get("screen_name", "Unknown")
            screen_type = analysis.get("screen_type", "unknown")
            description = analysis.get("description", "")
            interactive_elements = analysis.get("interactive_elements", [])

            # 4. Determine if this is a new or existing screen
            screen_id = await self._match_or_create_screen(
                screenshot, screen_name, screen_type, description, interactive_elements
            )
            self.current_screen_id = screen_id

            # Update status
            await self.server.update_status(
                current_screen=screen_name,
                total_screens=await self.graph.get_screen_count(),
                total_actions=self.total_actions,
                message=f"On screen: {screen_name}",
            )

            # 5. Get unexplored elements for this screen
            unexplored = await self.graph.get_unexplored_elements(screen_id)
            all_elements = await self.graph.get_elements_for_screen(screen_id)
            screen_data = await self.graph.get_screen(screen_id)
            is_fully_explored = screen_data.get("fully_explored", False) if screen_data else False

            # 6. Decide next action
            decision = self.strategy.decide_next_action(
                screen_id, unexplored, all_elements, is_fully_explored
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

            # 7. Execute action
            if action == "done":
                # Try to find another unexplored screen
                all_screens = await self.graph.get_all_screens()
                has_unexplored = any(
                    not s["fully_explored"] for s in all_screens
                )
                if not has_unexplored:
                    console.print("[success]🎉 All reachable screens explored![/success]")
                    break
                else:
                    # Mark current as explored and continue
                    await self.graph.mark_screen_explored(screen_id)
                    continue

            elif action == "tap" and element:
                coords = decision.get("coordinates", (0, 0))
                prev_screen_id = self.current_screen_id

                # Mark element as interacted
                await self.graph.mark_element_interacted(
                    element.get("id", ""), result=f"tapped"
                )

                # Execute tap
                success = await self.mcp.tap(int(coords[0]), int(coords[1]))
                if success:
                    self.total_actions += 1
                    await asyncio.sleep(self.action_delay)

                    # Check if screen changed
                    new_screenshot = await self.mcp.take_screenshot()
                    if new_screenshot:
                        comparison = await self.vision.compare_screens(
                            screenshot, new_screenshot
                        )
                        if not comparison.get("is_same_screen", True):
                            # New screen! Will be processed in next iteration.
                            self.current_screenshot = new_screenshot
                            self.strategy.reset_back_count()
                            console.print(
                                f"  [success]✨ New screen detected![/success] "
                                f"({comparison.get('reason', '')})"
                            )

            elif action == "back":
                prev_screen_id = self.current_screen_id
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
                # Type some test text into input fields
                await self.mcp.tap(
                    int(element.get("x", 0)), int(element.get("y", 0))
                )
                await asyncio.sleep(0.5)
                await self.mcp.type_text("test@example.com")
                await self.graph.mark_element_interacted(
                    element.get("id", ""), result="typed test text"
                )
                self.total_actions += 1
                await asyncio.sleep(self.action_delay)

            elif action == "skip":
                continue

            # Save state for resume
            save_exploration_state(
                {
                    "current_screen_id": self.current_screen_id,
                    "total_actions": self.total_actions,
                    "timestamp": time.time(),
                },
                self.state_file,
            )

            # Log action
            await self.graph.log_action(
                action_type=action,
                screen_id=screen_id,
                element_id=element.get("id", "") if element else "",
                detail=reason,
            )

    async def _match_or_create_screen(
        self,
        screenshot: bytes,
        name: str,
        screen_type: str,
        description: str,
        interactive_elements: list[dict],
    ) -> str:
        """
        Check if this screen was already seen (by comparing screenshots).
        If new, create it in the graph. If existing, return existing ID.
        """
        # Compare with previously seen screenshots
        for prev_id, prev_screenshot in self._previous_screenshots.items():
            try:
                comparison = await self.vision.compare_screens(prev_screenshot, screenshot)
                if comparison.get("is_same_screen", False) and comparison.get("similarity", 0) > 0.7:
                    logger.debug(f"Screen matches existing: {prev_id}")
                    # Update visit
                    await self.graph.add_screen(
                        prev_id, name, screen_type, description,
                        element_count=len(interactive_elements),
                    )
                    return prev_id
            except Exception as e:
                logger.debug(f"Screen comparison error: {e}")

        # New screen!
        screen_id = generate_screen_id()

        # Save screenshot
        screenshot_filename = f"{screen_id}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        save_screenshot(screenshot, screenshot_path)

        # Store for future comparison
        self._previous_screenshots[screen_id] = screenshot

        # Add to graph
        await self.graph.add_screen(
            screen_id=screen_id,
            name=name,
            screen_type=screen_type,
            description=description,
            screenshot_path=screenshot_filename,
            element_count=len(interactive_elements),
        )

        # Add elements to graph
        for el in interactive_elements:
            await self.graph.add_element(
                element_id=f"{screen_id}_{el.get('id', 'unknown')}",
                screen_id=screen_id,
                element_type=el.get("type", "unknown"),
                label=el.get("label", ""),
                x=int(el.get("x", 0)),
                y=int(el.get("y", 0)),
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

        # Notify web UI
        screen_data = await self.graph.get_screen(screen_id)
        if screen_data:
            await self.server.notify_new_screen(screen_data)

        console.print(
            f"  [success]📱 New screen:[/success] {name} ({screen_type}) "
            f"— {len(interactive_elements)} elements"
        )

        return screen_id

    async def _finish(self):
        """Finish exploration and print summary."""
        console.print("\n[bold cyan]═══ Exploration Complete ═══[/bold cyan]")

        screen_count = await self.graph.get_screen_count()
        transitions = await self.graph.get_all_transitions()
        vision_stats = self.vision.stats
        strategy_stats = self.strategy.stats

        console.print(f"  📱 Screens discovered:  {screen_count}")
        console.print(f"  🔗 Transitions:         {len(transitions)}")
        console.print(f"  👆 Total actions:        {self.total_actions}")
        console.print(f"  🔍 Vision API calls:     {vision_stats['requests']}")
        console.print(f"  📊 Total tokens:         {vision_stats['total_tokens']}")
        console.print()

        await self.server.update_status(
            state="complete",
            total_screens=screen_count,
            total_actions=self.total_actions,
            message=f"Exploration complete! {screen_count} screens found.",
        )

        # Keep server running for UI
        console.print(
            f"[info]🌐 Web UI still running at http://localhost:{self.config.ui.get('port', 3000)}[/info]"
        )
        console.print("[info]   Press Ctrl+C to stop[/info]\n")

        await self.cleanup(keep_server=True)

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


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="🔍 React Native Explorer Agent — Autonomously explore mobile apps"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from last saved exploration state",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--max-screens", "-m",
        type=int,
        default=None,
        help="Override max screens limit",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(
        log_dir=Path("./storage/logs"),
        verbose=args.verbose,
    )

    # Load config
    config = Config(args.config)

    # Override max screens if specified
    if args.max_screens:
        config._data["exploration"]["max_screens"] = args.max_screens

    # Create and run explorer
    explorer = Explorer(config, resume=args.resume)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        console.print("\n[warning]Shutting down...[/warning]")
        explorer.running = False

    signal.signal(signal.SIGINT, signal_handler)

    # Run
    try:
        asyncio.run(explorer.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
