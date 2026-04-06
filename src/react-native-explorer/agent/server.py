"""
REST API + WebSocket server for the Explorer Web UI.
Serves exploration data and provides real-time updates.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from aiohttp import web
import aiohttp_cors
import aiohttp

from .graph import ScreenGraph
from .utils import Config

logger = logging.getLogger("explorer.server")


class ExplorerServer:
    """HTTP API server that serves exploration data to the web UI."""

    def __init__(self, config: Config, graph: ScreenGraph):
        self.config = config
        self.graph = graph
        self.host = config.server.get("host", "127.0.0.1")
        self.port = config.server.get("port", 5100)
        self.screenshots_dir = Path(config.storage.get("screenshots_dir", "./storage/screenshots"))
        self.stories_dir = Path(config.storage.get("stories_dir", "./storage/stories"))
        self.stories_dir.mkdir(parents=True, exist_ok=True)

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._ws_clients: list[web.WebSocketResponse] = []
        self._exploration_status = {
            "state": "idle",
            "current_screen": None,
            "total_screens": 0,
            "total_actions": 0,
            "message": "Waiting to start",
        }

    async def start(self):
        """Start the HTTP server."""
        self._app = web.Application()

        # Setup CORS for Vite dev server
        cors = aiohttp_cors.setup(self._app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*",
            )
        })

        # Register routes — group by path so each resource is created once
        routes = [
            ("GET", "/api/graph", self._handle_graph),
            ("GET", "/api/screens", self._handle_screens),
            ("GET", "/api/screens/{screen_id}", self._handle_screen_detail),
            ("GET", "/api/screenshots/{filename}", self._handle_screenshot),
            ("GET", "/api/stories", self._handle_list_stories),
            ("POST", "/api/stories", self._handle_create_story),
            ("DELETE", "/api/stories/{story_id}", self._handle_delete_story),
            ("GET", "/api/status", self._handle_status),
            ("GET", "/ws/live", self._handle_websocket),
        ]

        # Group routes by path to avoid duplicate resource registration
        resources: dict[str, object] = {}
        for method, path, handler in routes:
            if path not in resources:
                resources[path] = cors.add(self._app.router.add_resource(path))
            cors.add(resources[path].add_route(method, handler))

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logger.info(f"🌐 API server running at http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
        # Close all WebSocket connections
        for ws in self._ws_clients:
            await ws.close()
        self._ws_clients.clear()

        if self._runner:
            await self._runner.cleanup()
            logger.info("🌐 API server stopped")

    # ── Status updates ───────────────────────────────────────────────

    async def update_status(self, **kwargs):
        """Update exploration status and notify WebSocket clients."""
        self._exploration_status.update(kwargs)
        await self._broadcast({
            "type": "status",
            "data": self._exploration_status,
        })

    async def notify_new_screen(self, screen: dict):
        """Notify WebSocket clients about a newly discovered screen."""
        await self._broadcast({
            "type": "new_screen",
            "data": screen,
        })

    async def notify_new_transition(self, transition: dict):
        """Notify WebSocket clients about a new transition."""
        await self._broadcast({
            "type": "new_transition",
            "data": transition,
        })

    async def notify_action(self, action: dict):
        """Notify WebSocket clients about an exploration action."""
        await self._broadcast({
            "type": "action",
            "data": action,
        })

    async def _broadcast(self, message: dict):
        """Broadcast a message to all connected WebSocket clients."""
        if not self._ws_clients:
            return

        text = json.dumps(message, default=str)
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_str(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_clients.remove(ws)

    # ── Route handlers ───────────────────────────────────────────────

    async def _handle_graph(self, request: web.Request) -> web.Response:
        """GET /api/graph — Full graph data for D3 visualization."""
        graph_data = await self.graph.export_graph_json()
        return web.json_response(graph_data)

    async def _handle_screens(self, request: web.Request) -> web.Response:
        """GET /api/screens — List all screens."""
        screens = await self.graph.get_all_screens()
        return web.json_response(screens)

    async def _handle_screen_detail(self, request: web.Request) -> web.Response:
        """GET /api/screens/:screen_id — Single screen with elements."""
        screen_id = request.match_info["screen_id"]
        screen = await self.graph.get_screen(screen_id)
        if not screen:
            return web.json_response({"error": "Screen not found"}, status=404)

        elements = await self.graph.get_elements_for_screen(screen_id)
        transitions = await self.graph.get_transitions_from(screen_id)
        screen["elements"] = elements
        screen["transitions"] = transitions
        return web.json_response(screen)

    async def _handle_screenshot(self, request: web.Request) -> web.Response:
        """GET /api/screenshots/:filename — Serve a screenshot file."""
        filename = request.match_info["filename"]
        filepath = self.screenshots_dir / filename
        if not filepath.exists():
            return web.json_response({"error": "Screenshot not found"}, status=404)
        return web.FileResponse(filepath)

    async def _handle_list_stories(self, request: web.Request) -> web.Response:
        """GET /api/stories — List all saved stories."""
        stories = []
        if self.stories_dir.exists():
            for f in self.stories_dir.glob("*.json"):
                try:
                    with open(f) as fh:
                        story = json.load(fh)
                        story["id"] = f.stem
                        stories.append(story)
                except Exception:
                    pass
        return web.json_response(stories)

    async def _handle_create_story(self, request: web.Request) -> web.Response:
        """POST /api/stories — Save a new story."""
        try:
            data = await request.json()
            import time
            story_id = f"story_{int(time.time())}"
            filepath = self.stories_dir / f"{story_id}.json"
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return web.json_response({"id": story_id, "status": "created"}, status=201)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_delete_story(self, request: web.Request) -> web.Response:
        """DELETE /api/stories/:story_id — Delete a story."""
        story_id = request.match_info["story_id"]
        filepath = self.stories_dir / f"{story_id}.json"
        if filepath.exists():
            filepath.unlink()
            return web.json_response({"status": "deleted"})
        return web.json_response({"error": "Story not found"}, status=404)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /api/status — Current exploration status."""
        return web.json_response(self._exploration_status)

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket endpoint for real-time exploration updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.append(ws)
        logger.info(f"📡 WebSocket client connected ({len(self._ws_clients)} total)")

        # Send current state on connect
        await ws.send_str(json.dumps({
            "type": "status",
            "data": self._exploration_status,
        }, default=str))

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Handle client messages if needed
                    pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        finally:
            if ws in self._ws_clients:
                self._ws_clients.remove(ws)
            logger.info(f"📡 WebSocket client disconnected ({len(self._ws_clients)} remaining)")

        return ws
