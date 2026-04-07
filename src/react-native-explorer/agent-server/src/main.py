"""FastAPI Agent Server - exposes exploration via REST API and WebSocket."""
import asyncio
import json
import logging
import os
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
from core.explorer import ExplorationEngine, ExplorationConfig
from core.executor import StoryExecutor
from core.vision import VisionAnalyzer
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
executor: Optional[StoryExecutor] = None
vision: Optional[VisionAnalyzer] = None
connected_websockets: List[WebSocket] = []


# Pydantic models
class StartRequest(BaseModel):
    max_screens: Optional[int] = None
    use_ai: Optional[bool] = True


class StoryCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[Dict] = []
    tags: List[str] = []
    priority: str = "medium"


class StoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict]] = None
    tags: Optional[List[str]] = None
    priority: Optional[str] = None


class StoryExecuteRequest(BaseModel):
    step_by_step: bool = False


class StepAddRequest(BaseModel):
    action: str
    screen_id: Optional[str] = None
    element_id: Optional[str] = None
    element_query: Optional[Dict] = None
    data: Dict = {}
    expected: Optional[str] = None
    assertion: Optional[str] = None


class ExecutionActionRequest(BaseModel):
    action: str  # pause, resume, stop, step


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


# Executor event handler
async def on_executor_event(event: str, data: Any):
    """Handle story executor events."""
    await broadcast(event, data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Server lifespan management."""
    global engine, executor, vision
    
    # Startup
    logger.info("Starting Agent Server...")
    await db.connect()
    
    # Initialize vision analyzer
    api_key = config.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
    if api_key:
        vision = VisionAnalyzer(api_key=api_key, model=config.vision_model)
        logger.info("Vision analyzer initialized")
    else:
        logger.warning("No OpenRouter API key found - AI vision disabled")
    
    # Initialize exploration engine
    exploration_config = ExplorationConfig(
        max_screens=config.max_screens,
        action_delay_ms=1500,
        use_ai_vision=api_key is not None
    )
    engine = ExplorationEngine(exploration_config, vision_analyzer=vision)
    engine.on_state_change(on_engine_event)
    
    # Initialize story executor
    executor = StoryExecutor(vision_analyzer=vision)
    executor.on_event(on_executor_event)
    
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
    description="AI-powered mobile app exploration and testing agent",
    version="2.1.0",
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


# === Health & Status ===

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "exploration_state": engine.state.value if engine else "unknown",
        "execution_state": executor.state.value if executor else "unknown"
    }


@app.get("/api/status")
async def get_status():
    """Get overall system status."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    
    exploration_status = await engine.get_status()
    execution_status = executor.get_status() if executor else {}
    
    return {
        "exploration": exploration_status,
        "execution": execution_status,
        "vision": vision.get_stats() if vision else {"enabled": False}
    }


# === Exploration API ===

@app.post("/api/exploration/start")
async def start_exploration(req: StartRequest):
    """Start exploration."""
    if not engine:
        raise HTTPException(503, "Engine not initialized")
    
    if req.max_screens:
        engine.config.max_screens = req.max_screens
    engine.config.use_ai_vision = req.use_ai if req.use_ai is not None else True
    
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
async def list_screens(screen_type: Optional[str] = None, limit: int = 100):
    """List all discovered screens."""
    if screen_type:
        screens = await db.fetchall(
            "SELECT * FROM screens WHERE screen_type = ? ORDER BY first_seen DESC LIMIT ?",
            (screen_type, limit)
        )
    else:
        screens = await db.fetchall(
            "SELECT * FROM screens ORDER BY first_seen DESC LIMIT ?",
            (limit,)
        )
    return {"screens": screens}


@app.get("/api/screens/{screen_id}")
async def get_screen(screen_id: str):
    """Get screen details with elements and transitions."""
    screen = await db.fetchone("SELECT * FROM screens WHERE id = ?", (screen_id,))
    if not screen:
        raise HTTPException(404, "Screen not found")
    
    elements = await db.fetchall(
        "SELECT * FROM elements WHERE screen_id = ? ORDER BY y, x",
        (screen_id,)
    )
    
    outgoing = await db.fetchall(
        """SELECT t.*, s.name as to_screen_name 
           FROM transitions t 
           LEFT JOIN screens s ON t.to_screen_id = s.id
           WHERE t.from_screen_id = ?""",
        (screen_id,)
    )
    
    incoming = await db.fetchall(
        """SELECT t.*, s.name as from_screen_name 
           FROM transitions t 
           LEFT JOIN screens s ON t.from_screen_id = s.id
           WHERE t.to_screen_id = ?""",
        (screen_id,)
    )
    
    return {
        **screen,
        "elements": elements,
        "outgoing_transitions": outgoing,
        "incoming_transitions": incoming
    }


@app.get("/api/screens/{screen_id}/elements")
async def get_screen_elements(screen_id: str, interactive_only: bool = False):
    """Get elements for a screen."""
    if interactive_only:
        elements = await db.get_untapped_elements(screen_id)
    else:
        elements = await db.get_screen_elements(screen_id)
    return {"elements": elements}


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve screenshot file."""
    from fastapi.responses import FileResponse
    
    screenshot_path = Path("./storage/screenshots") / filename
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
        "fully_explored": bool(s["fully_explored"]),
        "is_modal": bool(s["is_modal"]),
        "requires_auth": bool(s["requires_auth"]),
        "element_count": s["element_count"]
    } for s in screens]
    
    edges = [{
        "id": t["id"],
        "source": t["from_screen_id"],
        "target": t["to_screen_id"],
        "action": t["action_type"],
        "element_id": t["element_id"]
    } for t in transitions if t["to_screen_id"]]
    
    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get graph statistics."""
    screen_count = await db.fetchone("SELECT COUNT(*) as count FROM screens")
    transition_count = await db.fetchone("SELECT COUNT(*) as count FROM transitions")
    element_count = await db.fetchone("SELECT COUNT(*) as count FROM elements")
    
    screen_types = await db.fetchall(
        "SELECT screen_type, COUNT(*) as count FROM screens GROUP BY screen_type"
    )
    
    return {
        "screens": screen_count["count"],
        "transitions": transition_count["count"],
        "elements": element_count["count"],
        "screen_types": {s["screen_type"]: s["count"] for s in screen_types}
    }


@app.post("/api/reset")
async def reset_database(confirm: bool = False):
    """
    Reset the database - clear all exploration data.
    Use with caution! Set confirm=true to proceed.
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to reset database")
    
    # Stop any running exploration first
    if engine and engine.state.value in ["exploring", "paused"]:
        await engine.stop()
    
    # Clear all tables
    await db.execute("DELETE FROM execution_steps")
    await db.execute("DELETE FROM story_executions")
    await db.execute("DELETE FROM transitions")
    await db.execute("DELETE FROM elements")
    await db.execute("DELETE FROM screens")
    await db.execute("DELETE FROM screen_hash_mappings")
    await db.execute("DELETE FROM ai_analysis_cache")
    await db.execute("DELETE FROM exploration_log")
    await db.commit()
    
    # Clear vision cache if available
    if vision:
        vision._analysis_cache.clear()
    
    logger.info("Database reset complete")
    return {"status": "reset", "message": "All exploration data cleared"}


@app.get("/api/graph/path")
async def find_path(from_screen: str, to_screen: str):
    """Find shortest path between two screens."""
    # Check pre-computed paths
    path = await db.fetchone(
        "SELECT * FROM navigation_paths WHERE from_screen_id = ? AND to_screen_id = ?",
        (from_screen, to_screen)
    )
    
    if path:
        return {
            "from": from_screen,
            "to": to_screen,
            "path": json.loads(path["path_json"]),
            "actions": json.loads(path["action_sequence"] or "[]"),
            "distance": path["distance"]
        }
    
    # TODO: Implement BFS pathfinding
    return {"from": from_screen, "to": to_screen, "path": None, "error": "Path not found"}


# === Stories API ===

@app.get("/api/stories")
async def list_stories():
    """List all stories."""
    stories = await db.fetchall(
        "SELECT * FROM stories ORDER BY created_at DESC"
    )
    # Parse steps_json for each story
    for story in stories:
        story["steps"] = json.loads(story.get("steps_json", "[]"))
        del story["steps_json"]
    return {"stories": stories}


@app.post("/api/stories")
async def create_story(req: StoryCreate):
    """Create a new story."""
    import time
    import uuid
    
    story_id = str(uuid.uuid4())[:8]
    now = time.time()
    
    await db.execute(
        """INSERT INTO stories (id, name, description, tags, priority, created_at, updated_at, steps_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (story_id, req.name, req.description, json.dumps(req.tags), req.priority,
         now, now, json.dumps(req.steps))
    )
    await db.commit()
    
    return {"id": story_id, "status": "created"}


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    """Get story details."""
    story = await db.fetchone("SELECT * FROM stories WHERE id = ?", (story_id,))
    if not story:
        raise HTTPException(404, "Story not found")
    
    story["steps"] = json.loads(story.get("steps_json", "[]"))
    del story["steps_json"]
    
    # Get execution history
    executions = await db.fetchall(
        "SELECT * FROM story_executions WHERE story_id = ? ORDER BY started_at DESC",
        (story_id,)
    )
    story["executions"] = executions
    
    return story


@app.put("/api/stories/{story_id}")
async def update_story(story_id: str, req: StoryUpdate):
    """Update a story."""
    story = await db.fetchone("SELECT * FROM stories WHERE id = ?", (story_id,))
    if not story:
        raise HTTPException(404, "Story not found")
    
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = ?")
        params.append(req.name)
    if req.description is not None:
        updates.append("description = ?")
        params.append(req.description)
    if req.steps is not None:
        updates.append("steps_json = ?")
        params.append(json.dumps(req.steps))
    if req.tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(req.tags))
    if req.priority is not None:
        updates.append("priority = ?")
        params.append(req.priority)
    
    if updates:
        import time
        updates.append("updated_at = ?")
        params.append(time.time())
        params.append(story_id)
        
        await db.execute(
            f"UPDATE stories SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        await db.commit()
    
    return {"status": "updated"}


@app.delete("/api/stories/{story_id}")
async def delete_story(story_id: str):
    """Delete a story."""
    await db.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    await db.commit()
    return {"status": "deleted"}


@app.post("/api/stories/{story_id}/steps")
async def add_step(story_id: str, req: StepAddRequest):
    """Add a step to a story."""
    story = await db.fetchone("SELECT steps_json FROM stories WHERE id = ?", (story_id,))
    if not story:
        raise HTTPException(404, "Story not found")
    
    steps = json.loads(story["steps_json"])
    steps.append({
        "action": req.action,
        "screen_id": req.screen_id,
        "element_id": req.element_id,
        "element_query": req.element_query,
        "data": req.data,
        "expected": req.expected,
        "assertion": req.assertion
    })
    
    import time
    await db.execute(
        "UPDATE stories SET steps_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(steps), time.time(), story_id)
    )
    await db.commit()
    
    return {"status": "added", "step_count": len(steps)}


# === Story Execution API ===

@app.post("/api/stories/{story_id}/execute")
async def execute_story(story_id: str, req: StoryExecuteRequest):
    """Execute a story."""
    if not executor:
        raise HTTPException(503, "Executor not initialized")
    
    if executor.state.value in ["running", "paused"]:
        raise HTTPException(409, "Execution already in progress")
    
    # Start execution in background
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    
    async def run():
        try:
            result = await executor.execute_story(
                story_id, execution_id=execution_id, step_by_step=req.step_by_step
            )
            logger.info(f"Execution {execution_id} completed: {result.status.value}")
        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}")
    
    asyncio.create_task(run())
    
    return {
        "execution_id": execution_id,
        "story_id": story_id,
        "status": "started"
    }


@app.get("/api/executions")
async def list_executions(limit: int = 20):
    """List recent executions."""
    executions = await db.fetchall(
        """SELECT e.*, s.name as story_name 
           FROM story_executions e
           JOIN stories s ON e.story_id = s.id
           ORDER BY e.started_at DESC LIMIT ?""",
        (limit,)
    )
    return {"executions": executions}


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details with steps."""
    execution = await db.fetchone(
        """SELECT e.*, s.name as story_name, s.steps_json 
           FROM story_executions e
           JOIN stories s ON e.story_id = s.id
           WHERE e.id = ?""",
        (execution_id,)
    )
    if not execution:
        raise HTTPException(404, "Execution not found")
    
    steps = await db.fetchall(
        "SELECT * FROM execution_steps WHERE execution_id = ? ORDER BY step_number",
        (execution_id,)
    )
    
    execution["steps"] = steps
    execution["story_steps"] = json.loads(execution.get("steps_json", "[]"))
    del execution["steps_json"]
    
    return execution


@app.post("/api/executions/{execution_id}/control")
async def control_execution(execution_id: str, req: ExecutionActionRequest):
    """Control a running execution."""
    if not executor or executor._current_execution != execution_id:
        raise HTTPException(404, "Execution not found or not active")
    
    if req.action == "pause":
        await executor.pause()
    elif req.action == "resume":
        await executor.resume()
    elif req.action == "stop":
        await executor.stop()
    elif req.action == "step":
        await executor.step_forward()
    else:
        raise HTTPException(400, f"Unknown action: {req.action}")
    
    return {"status": executor.state.value}


@app.get("/api/executions/{execution_id}/screenshots/{filename}")
async def get_execution_screenshot(execution_id: str, filename: str):
    """Serve execution screenshot."""
    from fastapi.responses import FileResponse
    
    screenshot_path = Path("./storage/screenshots/executions") / filename
    if not screenshot_path.exists():
        raise HTTPException(404, "Screenshot not found")
    
    return FileResponse(screenshot_path)


# === Gallery API ===

@app.get("/api/gallery")
async def get_gallery(screen_type: Optional[str] = None, cluster_by: str = "type"):
    """Get gallery view of screens."""
    if screen_type:
        screens = await db.fetchall(
            "SELECT * FROM screens WHERE screen_type = ? ORDER BY first_seen DESC",
            (screen_type,)
        )
    else:
        screens = await db.fetchall("SELECT * FROM screens ORDER BY first_seen DESC")
    
    if cluster_by == "type":
        clusters = {}
        for s in screens:
            t = s["screen_type"]
            if t not in clusters:
                clusters[t] = []
            clusters[t].append(s)
        return {"clusters": clusters}
    
    return {"screens": screens}


@app.get("/api/gallery/clusters")
async def get_clusters():
    """Get screen clusters."""
    clusters = await db.fetchall(
        "SELECT screen_type, COUNT(*) as count FROM screens GROUP BY screen_type"
    )
    return {"clusters": [{"type": c["screen_type"], "count": c["count"]} for c in clusters]}


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
                "event": "exploration_status",
                "data": status
            }))
        
        if executor:
            await websocket.send_text(json.dumps({
                "event": "execution_status",
                "data": executor.get_status()
            }))
        
        # Handle client messages
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            action = data.get("action")
            if action == "exploration_start":
                await engine.start()
            elif action == "exploration_pause":
                await engine.pause()
            elif action == "exploration_resume":
                await engine.resume()
            elif action == "exploration_stop":
                await engine.stop()
            elif action == "execution_pause":
                if executor:
                    await executor.pause()
            elif action == "execution_resume":
                if executor:
                    await executor.resume()
            elif action == "execution_stop":
                if executor:
                    await executor.stop()
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
