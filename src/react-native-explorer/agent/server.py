"""
Enhanced REST API + WebSocket server for the Explorer Web UI.
Serves exploration data, story management, and provides real-time updates.
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
            "message": "📡 Agent Ready - Press Play to Start Exploration",
            "stats": {},
        }
        
        # Linked explorer instance for direct control
        self.explorer = None

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

        # Register routes
        routes = [
            # Graph & Screens
            ("GET", "/api/graph", self._handle_graph),
            ("GET", "/api/graph/stats", self._handle_graph_stats),
            ("GET", "/api/screens", self._handle_screens),
            ("GET", "/api/screens/{screen_id}", self._handle_screen_detail),
            ("GET", "/api/screens/{screen_id}/path/{target_id}", self._handle_screen_path),
            ("GET", "/api/screens/search", self._handle_screen_search),
            
            # Gallery
            ("GET", "/api/gallery", self._handle_gallery),
            ("GET", "/api/gallery/clusters", self._handle_gallery_clusters),
            ("GET", "/api/gallery/by-type/{screen_type}", self._handle_gallery_by_type),
            
            # Screenshots
            ("GET", "/api/screenshots/{filename}", self._handle_screenshot),
            
            # Stories
            ("GET", "/api/stories", self._handle_list_stories),
            ("POST", "/api/stories", self._handle_create_story),
            ("GET", "/api/stories/{story_id}", self._handle_get_story),
            ("PUT", "/api/stories/{story_id}", self._handle_update_story),
            ("DELETE", "/api/stories/{story_id}", self._handle_delete_story),
            ("POST", "/api/stories/{story_id}/steps", self._handle_add_story_step),
            ("POST", "/api/stories/{story_id}/export/{format}", self._handle_export_story),
            ("POST", "/api/stories/generate-from-path", self._handle_generate_story_from_path),
            ("POST", "/api/stories/auto-generate", self._handle_auto_generate_stories),
            
            # Exports (JSON-wrapped)
            ("GET", "/api/export/detox", self._handle_export_detox),
            ("GET", "/api/export/maestro", self._handle_export_maestro),
            ("GET", "/api/export/appium", self._handle_export_appium),
            ("GET", "/api/export/full", self._handle_export_full),
            
            # Exports (Direct file download)
            ("GET", "/api/export/detox/download", self._handle_download_detox),
            ("GET", "/api/export/maestro/download", self._handle_download_maestro),
            ("GET", "/api/export/appium/download", self._handle_download_appium),
            
            # Live emulator screenshot
            ("GET", "/api/live-screenshot", self._handle_live_screenshot),
            
            # Storage Management
            ("DELETE", "/api/storage", self._handle_clear_storage),
            ("GET", "/api/export/zip", self._handle_export_zip),
            
            # Agent Control
            ("POST", "/api/agent/start", self._handle_agent_start),
            ("POST", "/api/agent/pause", self._handle_agent_pause),
            ("POST", "/api/agent/stop", self._handle_agent_stop),
            ("GET", "/api/agent/logs", self._handle_agent_logs),
            ("GET", "/api/status", self._handle_status),
            
            # WebSocket
            ("GET", "/ws/live", self._handle_websocket),
        ]

        # Group routes by path
        resources: dict[str, object] = {}
        for method, path, handler in routes:
            if path not in resources:
                resources[path] = cors.add(self._app.router.add_resource(path))
            cors.add(resources[path].add_route(method, handler))

        # Setup static file serving for UI (AFTER API routes)
        # 🔧 Fix: Serve the built UI from the root-level 'ui' folder
        ui_dir = Path(self.config.ui.get("static_dir", "./ui")).resolve()
        if ui_dir.exists():
            # Add static files
            self._app.router.add_static('/', ui_dir, show_index=True)
            logger.info(f"UI static files served from: {ui_dir}")
        else:
            logger.warning(f"UI directory not found: {ui_dir}")

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        print(f"\n[EXPLORER SERVER] 🚀 SERVER READY: Listening on http://{self.host}:{self.port}\n", flush=True)
        logger.info(f"API server running at http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
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

    async def _handle_graph_stats(self, request: web.Request) -> web.Response:
        """GET /api/graph/stats — Graph statistics."""
        screen_count = await self.graph.get_screen_count()
        transitions = await self.graph.get_all_transitions()
        clusters = await self.graph.get_clusters()
        
        return web.json_response({
            "total_screens": screen_count,
            "total_transitions": len(transitions),
            "total_clusters": len(clusters),
            "screens_by_type": {},  # Could be populated from DB
        })

    async def _handle_screens(self, request: web.Request) -> web.Response:
        """GET /api/screens — List all screens with optional filtering."""
        cluster_id = request.query.get("cluster")
        screen_type = request.query.get("type")
        
        screens = await self.graph.get_all_screens(cluster_id=cluster_id)
        
        if screen_type:
            screens = [s for s in screens if s.get("screen_type") == screen_type]
        
        return web.json_response(screens)

    async def _handle_screen_detail(self, request: web.Request) -> web.Response:
        """GET /api/screens/:screen_id — Single screen with elements."""
        screen_id = request.match_info["screen_id"]
        screen = await self.graph.get_screen(screen_id)
        if not screen:
            return web.json_response({"error": "Screen not found"}, status=404)

        elements = await self.graph.get_elements_for_screen(screen_id)
        transitions = await self.graph.get_transitions_from(screen_id)
        features = await self.graph.get_screen_features(screen_id)
        
        screen["elements"] = elements
        screen["transitions"] = transitions
        screen["features"] = features
        return web.json_response(screen)

    async def _handle_screen_path(self, request: web.Request) -> web.Response:
        """GET /api/screens/:screen_id/path/:target_id — Shortest path."""
        from_id = request.match_info["screen_id"]
        to_id = request.match_info["target_id"]
        
        path = await self.graph.get_shortest_path(from_id, to_id)
        if not path:
            return web.json_response({"error": "No path found"}, status=404)
        
        # Get full screen details for path
        path_details = []
        for screen_id in path:
            screen = await self.graph.get_screen(screen_id)
            if screen:
                path_details.append(screen)
        
        return web.json_response({
            "path": path,
            "screens": path_details,
        })

    async def _handle_screen_search(self, request: web.Request) -> web.Response:
        """GET /api/screens/search?q=query — Search screens."""
        query = request.query.get("q", "")
        if not query:
            return web.json_response({"error": "Query parameter 'q' required"}, status=400)
        
        screens = await self.graph.search_screens(query)
        return web.json_response(screens)

    # ── Gallery endpoints ────────────────────────────────────────────

    async def _handle_gallery(self, request: web.Request) -> web.Response:
        """GET /api/gallery — Get all screens for gallery view."""
        screens = await self.graph.get_all_screens()
        
        # Group by screen type
        by_type: dict[str, list] = {}
        for screen in screens:
            screen_type = screen.get("screen_type", "unknown")
            if screen_type not in by_type:
                by_type[screen_type] = []
            by_type[screen_type].append(screen)
        
        return web.json_response({
            "total": len(screens),
            "by_type": by_type,
            "screens": screens,
        })

    async def _handle_gallery_clusters(self, request: web.Request) -> web.Response:
        """GET /api/gallery/clusters — Get clustered screen gallery."""
        clusters = await self.graph.get_clusters()
        
        result = []
        for cluster in clusters:
            screens = await self.graph.get_all_screens(cluster_id=cluster["id"])
            result.append({
                **cluster,
                "screens": screens,
                "screen_count": len(screens),
            })
        
        return web.json_response(result)

    async def _handle_gallery_by_type(self, request: web.Request) -> web.Response:
        """GET /api/gallery/by-type/:screen_type — Get screens of specific type."""
        screen_type = request.match_info["screen_type"]
        screens = await self.graph.get_all_screens()
        
        filtered = [s for s in screens if s.get("screen_type") == screen_type]
        return web.json_response({
            "type": screen_type,
            "count": len(filtered),
            "screens": filtered,
        })

    # ── Screenshots ──────────────────────────────────────────────────

    async def _handle_screenshot(self, request: web.Request) -> web.Response:
        """GET /api/screenshots/:filename — Serve a screenshot file."""
        filename = request.match_info["filename"]
        filepath = self.screenshots_dir / filename
        if not filepath.exists():
            return web.json_response({"error": "Screenshot not found"}, status=404)
        return web.FileResponse(filepath)

    # ── Stories ──────────────────────────────────────────────────────

    async def _handle_list_stories(self, request: web.Request) -> web.Response:
        """GET /api/stories — List all saved stories."""
        stories = await self.graph.get_stories()
        return web.json_response(stories)

    async def _handle_create_story(self, request: web.Request) -> web.Response:
        """POST /api/stories — Save a new story."""
        try:
            data = await request.json()
            from .utils import generate_story_id
            
            story_id = generate_story_id()
            await self.graph.create_story(
                story_id=story_id,
                name=data.get("name", "Untitled Story"),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                priority=data.get("priority", "medium"),
            )
            
            # Add steps if provided
            for i, step in enumerate(data.get("steps", [])):
                await self.graph.add_story_step(
                    story_id=story_id,
                    step_number=i + 1,
                    action_type=step.get("action_type", "tap"),
                    screen_id=step.get("screen_id"),
                    element_id=step.get("element_id"),
                    coordinates=step.get("coordinates"),
                    data=step.get("data"),
                    assertion=step.get("assertion", ""),
                )
            
            return web.json_response({"id": story_id, "status": "created"}, status=201)
        except Exception as e:
            logger.exception("Failed to create story")
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_get_story(self, request: web.Request) -> web.Response:
        """GET /api/stories/:story_id — Get story with all steps."""
        story_id = request.match_info["story_id"]
        story = await self.graph.get_story(story_id)
        if not story:
            return web.json_response({"error": "Story not found"}, status=404)
        return web.json_response(story)

    async def _handle_update_story(self, request: web.Request) -> web.Response:
        """PUT /api/stories/:story_id — Update story."""
        story_id = request.match_info["story_id"]
        try:
            data = await request.json()
            # For now, delete and recreate
            await self.graph.delete_story(story_id)
            await self.graph.create_story(
                story_id=story_id,
                name=data.get("name", "Untitled"),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                priority=data.get("priority", "medium"),
            )
            return web.json_response({"status": "updated"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_delete_story(self, request: web.Request) -> web.Response:
        """DELETE /api/stories/:story_id — Delete a story."""
        story_id = request.match_info["story_id"]
        await self.graph.delete_story(story_id)
        return web.json_response({"status": "deleted"})

    async def _handle_add_story_step(self, request: web.Request) -> web.Response:
        """POST /api/stories/:story_id/steps — Add a step to a story."""
        story_id = request.match_info["story_id"]
        try:
            data = await request.json()
            
            # Get current step count
            story = await self.graph.get_story(story_id)
            if not story:
                return web.json_response({"error": "Story not found"}, status=404)
            
            step_number = len(story.get("steps", [])) + 1
            
            step_id = await self.graph.add_story_step(
                story_id=story_id,
                step_number=step_number,
                action_type=data.get("action_type", "tap"),
                screen_id=data.get("screen_id"),
                element_id=data.get("element_id"),
                coordinates=data.get("coordinates"),
                data=data.get("data"),
                assertion=data.get("assertion", ""),
            )
            
            return web.json_response({"id": step_id, "status": "added"}, status=201)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_generate_story_from_path(self, request: web.Request) -> web.Response:
        """POST /api/stories/generate-from-path — Auto-generate story from path."""
        try:
            data = await request.json()
            screen_ids = data.get("screen_ids", [])
            name = data.get("name", "Generated Story")
            
            if not screen_ids:
                return web.json_response({"error": "screen_ids required"}, status=400)
            
            if hasattr(self, 'explorer'):
                story_id = await self.explorer.create_story_from_path(screen_ids, name)
                return web.json_response({"id": story_id, "status": "created"}, status=201)
            
            return web.json_response({"error": "Explorer not linked"}, status=500)
        except Exception as e:
            logger.exception("Failed to generate story")
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_auto_generate_stories(self, request: web.Request) -> web.Response:
        """POST /api/stories/auto-generate — Use AI to auto-generate Given/When/Then stories from the graph."""
        if not self.explorer or not self.explorer.vision:
            return web.json_response({"error": "Explorer/vision not available"}, status=503)
        
        try:
            # Get all screens and transitions from the graph
            all_screens = await self.graph.get_all_screens()
            if len(all_screens) < 2:
                return web.json_response({"error": "Need at least 2 screens to generate stories"}, status=400)
            
            # Collect transitions
            all_transitions = []
            for screen in all_screens:
                transitions = await self.graph.get_transitions_from(screen["id"])
                all_transitions.extend(transitions)
            
            # Use AI to generate stories
            story_data = await self.explorer.vision.generate_story_from_screens(
                all_screens, all_transitions
            )
            
            if not story_data or not story_data.get("name"):
                return web.json_response({"error": "Story generation returned empty result"}, status=500)
            
            # Save to database
            from .utils import generate_story_id
            story_id = generate_story_id()
            
            await self.graph.create_story(
                story_id=story_id,
                name=story_data.get("name", "Auto-generated Story"),
                description=story_data.get("description", ""),
                tags=story_data.get("tags", ["auto", "ai-generated"]),
            )
            
            # Add steps
            for step in story_data.get("steps", []):
                await self.graph.add_story_step(
                    story_id=story_id,
                    step_number=step.get("step_number", 0),
                    action_type=step.get("action_type", "navigate"),
                    screen_id=step.get("screen_id", ""),
                    element_id=step.get("element_id", ""),
                    assertion=step.get("assertion", ""),
                    data=step,
                )
            
            return web.json_response({
                "id": story_id,
                "story": story_data,
                "status": "created",
            }, status=201)
            
        except Exception as e:
            logger.exception("Auto story generation failed")
            return web.json_response({"error": str(e)}, status=500)

    # ── Export handlers ──────────────────────────────────────────────

    async def _handle_export_story(self, request: web.Request) -> web.Response:
        """POST /api/stories/:story_id/export/:format — Export story to E2E format."""
        story_id = request.match_info["story_id"]
        format_name = request.match_info["format"]
        
        story = await self.graph.get_story(story_id)
        if not story:
            return web.json_response({"error": "Story not found"}, status=404)
        
        # Export based on format
        from .exporters import export_story
        try:
            exported = export_story(story, format_name)
            await self.graph.update_story_export(story_id, format_name)
            
            return web.json_response({
                "format": format_name,
                "content": exported,
                "filename": f"{story['name']}.{format_name}",
            })
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _handle_export_detox(self, request: web.Request) -> web.Response:
        """GET /api/export/detox — Export all stories as Detox tests."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_detox
        
        content = export_to_detox(stories)
        return web.json_response({
            "format": "detox",
            "content": content,
            "filename": "e2e.test.js",
        })

    async def _handle_export_maestro(self, request: web.Request) -> web.Response:
        """GET /api/export/maestro — Export all stories as Maestro flows."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_maestro
        
        flows = export_to_maestro(stories)
        return web.json_response({
            "format": "maestro",
            "flows": flows,
        })

    async def _handle_export_appium(self, request: web.Request) -> web.Response:
        """GET /api/export/appium — Export all stories as Appium tests."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_appium
        
        content = export_to_appium(stories)
        return web.json_response({
            "format": "appium",
            "content": content,
            "filename": "test_appium.py",
        })

    async def _handle_export_full(self, request: web.Request) -> web.Response:
        """GET /api/export/full — Export complete exploration data."""
        data = await self.graph.export_for_e2e()
        return web.json_response(data)

    async def _handle_download_detox(self, request: web.Request) -> web.Response:
        """GET /api/export/detox/download — Download Detox test file."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_detox
        content = export_to_detox(stories)
        return web.Response(
            text=content,
            content_type='application/javascript',
            headers={'Content-Disposition': 'attachment; filename="e2e.test.js"'},
        )

    async def _handle_download_maestro(self, request: web.Request) -> web.Response:
        """GET /api/export/maestro/download — Download Maestro flow file."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_maestro
        flows = export_to_maestro(stories)
        # Concatenate all flows into one YAML
        import yaml
        content = ''
        for name, flow_yaml in flows.items():
            content += f"# === Flow: {name} ===\n{flow_yaml}\n\n"
        return web.Response(
            text=content,
            content_type='application/x-yaml',
            headers={'Content-Disposition': 'attachment; filename="flows.yaml"'},
        )

    async def _handle_download_appium(self, request: web.Request) -> web.Response:
        """GET /api/export/appium/download — Download Appium test file."""
        stories = await self.graph.get_stories()
        from .exporters import export_to_appium
        content = export_to_appium(stories)
        return web.Response(
            text=content,
            content_type='text/x-python',
            headers={'Content-Disposition': 'attachment; filename="test_appium.py"'},
        )

    async def _handle_live_screenshot(self, request: web.Request) -> web.Response:
        """GET /api/live-screenshot — Get a live screenshot from the emulator."""
        if not self.explorer or not self.explorer.mcp or not self.explorer.mcp.is_connected:
            return web.json_response({"error": "Emulator not connected"}, status=503)
        try:
            screenshot = await self.explorer.mcp.take_screenshot()
            if screenshot:
                import base64
                b64 = base64.b64encode(screenshot).decode('utf-8')
                return web.json_response({"image": f"data:image/png;base64,{b64}"})
            return web.json_response({"error": "Screenshot failed"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_export_zip(self, request: web.Request) -> web.Response:
        """GET /api/export/zip — Export all data as ZIP."""
        import zipfile
        import io
        import time
        
        # Create in-memory ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add graph data
            graph_data = await self.graph.export_graph_json()
            zip_file.writestr('graph.json', json.dumps(graph_data, indent=2))
            
            # Add stories
            stories = await self.graph.get_stories()
            zip_file.writestr('stories.json', json.dumps(stories, indent=2))
            
            # Add screenshots
            for screenshot_file in self.screenshots_dir.glob('*.png'):
                zip_file.write(screenshot_file, f'screenshots/{screenshot_file.name}')
        
        zip_buffer.seek(0)
        
        return web.Response(
            body=zip_buffer.read(),
            headers={
                'Content-Type': 'application/zip',
                'Content-Disposition': f'attachment; filename="exploration_export_{int(time.time())}.zip"',
            }
        )

    # ── Storage Management ───────────────────────────────────────────

    async def _handle_clear_storage(self, request: web.Request) -> web.Response:
        """DELETE /api/storage — Clear all data."""
        if self.screenshots_dir.exists():
            for child in self.screenshots_dir.iterdir():
                if child.is_file():
                    child.unlink()
        if self.stories_dir.exists():
            for child in self.stories_dir.iterdir():
                if child.is_file():
                    child.unlink()
        await self.graph.clear()
        
        self._exploration_status = {
            "state": "idle",
            "current_screen": None,
            "total_screens": 0,
            "total_actions": 0,
            "message": "Storage cleared",
        }
        await self._broadcast({"type": "status", "data": self._exploration_status})
        
        return web.json_response({"status": "cleared"})

    # ── Agent Control ────────────────────────────────────────────────

    async def _handle_agent_start(self, request: web.Request) -> web.Response:
        """POST /api/agent/start — Start or resume exploration."""
        if self.explorer:
            self.explorer.pause_event.set()
            self.explorer.paused = False
            self._exploration_status["state"] = "exploring"
            return web.json_response({"status": "started", "message": "Agent resumed"})
        
        return web.json_response({"error": "Explorer instance not found in server"}, status=500)

    async def _handle_agent_pause(self, request: web.Request) -> web.Response:
        """POST /api/agent/pause — Pause exploration."""
        if self.explorer:
            self.explorer.pause_event.clear()
            self.explorer.paused = True
            self._exploration_status["state"] = "paused"
            return web.json_response({"status": "paused"})
        
        return web.json_response({"error": "Explorer not available"}, status=500)
    async def _handle_agent_stop(self, request: web.Request) -> web.Response:
        """POST /api/agent/stop — Stop exploration."""
        if hasattr(self, 'explorer') and self.explorer:
            self.explorer.running = False
            self.explorer.pause_event.set()
            self._exploration_status["state"] = "idle"
            return web.json_response({"status": "stopped"})
        
        return web.json_response({"error": "Explorer not available"}, status=500)

    async def _handle_agent_logs(self, request: web.Request) -> web.Response:
        """GET /api/agent/logs — Get recent explorer logs."""
        # For unified mode, we can just return an empty list or implement in-memory logs
        return web.json_response({"logs": []})

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /api/status — Current exploration status."""
        # Status is updated directly by explorer via update_status()
        status = dict(self._exploration_status)
        status["managed_mode"] = False
        return web.json_response(status)

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket endpoint for real-time exploration updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.append(ws)
        logger.info(f"📡 WebSocket client connected ({len(self._ws_clients)} total)")

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
