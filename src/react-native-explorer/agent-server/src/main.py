"""FastAPI Agent Server - exposes exploration via REST API and WebSocket."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import AgentConfig
from core.database import db
from core.explorer import ExplorationEngine
from mcp_client.client import MCPClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent.server")

# Global state
config = AgentConfig.from_env()
engine: Optional[ExplorationEngine] = None
connected_websockets: List[WebSocket] = []


# Pydantic models
class StartRequest(BaseModel):
    package_name: Optional[str] = None
    max_screens: Optional[int] = None


class StoryCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[Dict] = []


# WebSocket broadcast
async def broadcast(event: str, data: Any):
    """Broadcast message to all connected WebSockets."""
    message = json.dumps({"event": event, "data": data})
    disconnected = []
    
    for ws in connected_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


# Engine event handler
async def on_engine_event(event: str, data: Any):
    """Handle exploration engine events."""
    await broadcast(event, data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Server lifespan management."""
    global engine
    
    # Startup
    logger.info("Starting Agent Server...")
    await db.connect()
    
    engine = ExplorationEngine(config)
    engine.on_state_change(on_engine_event)
    
    logger.info(f"Agent Server ready on http://{config.host}:{config.port}")
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if engine:
        await engine.stop()
    await db.close()


# Create app
app = FastAPI(
    title="React Native Explorer Agent",
    description="AI-powered mobile app exploration agent",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === REST API ===

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "state": engine.state.value if engine else "unknown"}


@app.get("/api/status")
async def get_status():
    """Get exploration status."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    return await engine.get_status()


@app.post("/api/exploration/start")
async def start_exploration(req: StartRequest):
    """Start exploration."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    
    if req.max_screens:
        engine.config.max_screens = req.max_screens
    
    result = await engine.start()
    return result


@app.post("/api/exploration/pause")
async def pause_exploration():
    """Pause exploration."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    return await engine.pause()


@app.post("/api/exploration/resume")
async def resume_exploration():
    """Resume exploration."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    return await engine.resume()


@app.post("/api/exploration/stop")
async def stop_exploration():
    """Stop exploration."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    return await engine.stop()


# === Screens API ===

@app.get("/api/screens")
async def list_screens():
    """List all discovered screens."""
    screens = await db.fetchall(
        "SELECT * FROM screens ORDER BY first_seen DESC"
    )
    return {"screens": screens}


@app.get("/api/screens/{screen_id}")
async def get_screen(screen_id: str):
    """Get screen details with elements."""
    screen = await db.fetchone("SELECT * FROM screens WHERE id = ?", (screen_id,))
    if not screen:
        raise HTTPException(404, "Screen not found")
    
    elements = await db.fetchall(
        "SELECT * FROM elements WHERE screen_id = ?", (screen_id,)
    )
    transitions = await db.fetchall(
        "SELECT * FROM transitions WHERE from_screen_id = ?", (screen_id,)
    )
    
    return {
        **screen,
        "elements": elements,
        "transitions": transitions
    }


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve screenshot file."""
    from fastapi.responses import FileResponse
    
    screenshot_path = Path(config.screenshots_dir) / filename
    if not screenshot_path.exists():
        raise HTTPException(404, "Screenshot not found")
    
    return FileResponse(screenshot_path)


# === Graph API ===

@app.get("/api/graph")
async def get_graph():
    """Get full navigation graph."""
    screens = await db.fetchall("SELECT * FROM screens")
    transitions = await db.fetchall("SELECT * FROM transitions")
    
    nodes = [{
        "id": s["id"],
        "name": s["name"],
        "type": s["screen_type"],
        "screenshot": s["screenshot_path"],
        "visit_count": s["visit_count"],
        "fully_explored": bool(s["fully_explored"])
    } for s in screens]
    
    edges = [{
        "id": t["id"],
        "source": t["from_screen_id"],
        "target": t["to_screen_id"],
        "action": t["action_type"]
    } for t in transitions if t["to_screen_id"]]
    
    return {"nodes": nodes, "edges": edges}


# === Stories API ===

@app.get("/api/stories")
async def list_stories():
    """List all stories."""
    stories = await db.fetchall("SELECT * FROM stories ORDER BY created_at DESC")
    return {"stories": stories}


@app.post("/api/stories")
async def create_story(req: StoryCreate):
    """Create a new story."""
    import time
    import uuid
    
    story_id = str(uuid.uuid4())[:8]
    now = time.time()
    
    await db.execute(
        """INSERT INTO stories (id, name, description, created_at, updated_at, steps_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (story_id, req.name, req.description, now, now, json.dumps(req.steps))
    )
    await db.commit()
    
    return {"id": story_id, "status": "created"}


@app.delete("/api/stories/{story_id}")
async def delete_story(story_id: str):
    """Delete a story."""
    await db.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    await db.commit()
    return {"status": "deleted"}


# === WebSocket ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    connected_websockets.append(websocket)
    
    try:
        # Send current status
        if engine:
            status = await engine.get_status()
            await websocket.send_text(json.dumps({
                "event": "status",
                "data": status
            }))
        
        # Keep connection alive and handle client messages
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            # Handle client commands
            action = data.get("action")
            if action == "start":
                await engine.start()
            elif action == "pause":
                await engine.pause()
            elif action == "resume":
                await engine.resume()
            elif action == "stop":
                await engine.stop()
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
