"""
CLI entry point for the React Native Explorer Agent.
"""

import argparse
import asyncio
import logging
import signal
import sys
import webbrowser
from pathlib import Path

# Force UTF-8 output on Windows to prevent emoji/unicode crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .explorer import Explorer
from .utils import Config, console, setup_logging
from .server import ExplorerServer
from .graph import ScreenGraph

logger = logging.getLogger("explorer")


def serve_ui_only(config: Config, resume: bool = False):
    """Run the web UI server and host the explorer agent in the same process."""
    async def run_ui_with_agent():
        # 1. Initialize Shared Components
        graph = ScreenGraph(config.storage.get("database", "./storage/graph.db"))
        
        try:
            # 2. Connect to Database (with timeout from graph.py)
            console.print("[info]🔌 Connecting to database...[/info]")
            await graph.connect()
            
            # 3. Initialize Agent with shared graph (starts in PAUSED state)
            explorer = Explorer(config, resume=resume, graph=graph)
            server = explorer.server
            
            # 4. Start Server (Listen on port 5100)
            console.print("[info]🌐 Starting API server on port 5100...[/info]")
            await server.start()
            
            # 🔧 Unified UI Strategy:
            # We launch the background task immediately. It will wait internally 
            # for the `pause_event` to be set (by clicking 'Play' in the UI).
            explorer_task = asyncio.create_task(explorer.start_managed())
            
            # 🔧 Fixed: Point to Unified Port (5100) for UI
            ui_port = 5100 # Served by Python
            console.print(f"\n[success]✨ Unified Explorer READY at http://localhost:{ui_port}[/success]")
            console.print("[info]   Press 'Play' in the Dashboard to begin exploration.[/info]\n")
            
            # 5. Open browser automatically
            if config.ui.get("auto_open", True):
                import webbrowser
                target_url = f"http://localhost:{ui_port}"
                webbrowser.open(target_url)
            
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                # Handle Ctrl+C from asyncio.run()
                pass
        except Exception as e:
            console.print(f"\n[error]❌ Fatal Startup Error: {e}[/error]")
            console.print("[warning]Check if port 5100 is already in use by another process.[/warning]\n")
        finally:
            # 🔧 Fixed: Clean shutdown of all components
            if 'explorer_task' in locals():
                explorer_task.cancel()
                try:
                    await explorer_task
                except asyncio.CancelledError:
                    pass
            if 'server' in locals():
                await server.stop()
            if 'graph' in locals():
                await graph.close()
            console.print("[info]🧹 Cleanup complete. All processes stopped.[/info]")
    
    try:
        asyncio.run(run_ui_with_agent())
    except KeyboardInterrupt:
        pass


async def run_explorer_managed(config, resume=False):
    """Run explorer in managed mode (no server, communicates via stdout)."""
    from .explorer import Explorer
    
    print("=" * 60, flush=True)
    print("[EXPLORER] Starting managed explorer subprocess", flush=True)
    print(f"[EXPLORER] Config: {getattr(config, 'config_path', 'default')}", flush=True)
    print(f"[EXPLORER] Resume: {resume}", flush=True)
    print("=" * 60, flush=True)
    
    explorer = Explorer(config, resume=resume)
    
    # Override server to no-op mode for managed execution
    explorer._managed_mode = True
    
    try:
        await explorer.start_managed()
    except Exception as e:
        print(f"[ERROR] Explorer failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="🔍 React Native Explorer Agent — Autonomously explore mobile apps and generate E2E tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agent                    # Start exploration
  python -m agent --ui-only          # Run web UI only (no exploration)
  python -m agent --resume           # Resume from last state
  python -m agent --max-screens 100  # Explore up to 100 screens
  python -m agent --config custom.yaml
        """
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
    parser.add_argument(
        "--ui-only", "-u",
        action="store_true",
        help="Run only the web UI server (no exploration)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all stored data before starting",
    )
    parser.add_argument(
        "--managed",
        action="store_true",
        help=argparse.SUPPRESS,  # Internal use only - run explorer without server
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(
        log_dir=Path("./storage/logs"),
        verbose=args.verbose,
    )

    # Load config
    try:
        config = Config(args.config)
    except SystemExit:
        return

    # Override max screens if specified
    if args.max_screens:
        config._data["exploration"]["max_screens"] = args.max_screens

    # Handle clear storage
    if args.clear:
        console.print("[warning]Clearing all stored data...[/warning]")
        import shutil
        storage_dir = Path("./storage")
        if storage_dir.exists():
            for subdir in ["screenshots", "cache", "stories"]:
                path = storage_dir / subdir
                if path.exists():
                    shutil.rmtree(path)
            # Clear database
            db_path = storage_dir / "graph.db"
            if db_path.exists():
                db_path.unlink()
        console.print("[success]Storage cleared![/success]\n")

    # UI Mode (Unified)
    if args.ui_only:
        console.print("[info]Starting in Unified UI mode...[/info]")
        serve_ui_only(config, resume=args.resume)
        return
    
    # Managed mode (run explorer without server - for subprocess use)
    if args.managed:
        asyncio.run(run_explorer_managed(config, resume=args.resume))
        return

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
