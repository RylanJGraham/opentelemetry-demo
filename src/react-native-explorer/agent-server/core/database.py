"""Database models and connection for the agent server."""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

try:
    import aiosqlite
except ImportError:
    aiosqlite = None


# Enhanced schema with rich mapping support
SCHEMA = """
-- Screens discovered during exploration
CREATE TABLE IF NOT EXISTS screens (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    screen_type TEXT DEFAULT 'unknown',
    description TEXT DEFAULT '',
    screenshot_path TEXT,
    
    -- Multi-level hashing for caching
    content_hash TEXT UNIQUE,  -- SHA-256 of screenshot
    perceptual_hash TEXT,      -- pHash for visual similarity
    structure_hash TEXT,       -- Layout fingerprint
    element_structure_hash TEXT,  -- Hash based on element positions
    
    -- Statistics
    element_count INTEGER DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    visit_count INTEGER DEFAULT 1,
    fully_explored INTEGER DEFAULT 0,
    
    -- AI Analysis
    ai_confidence REAL DEFAULT 0.0,
    is_modal INTEGER DEFAULT 0,
    is_error_state INTEGER DEFAULT 0,
    requires_auth INTEGER DEFAULT 0,
    ai_metadata TEXT DEFAULT '{}',  -- JSON blob for extensibility
    
    -- Navigation info
    depth_from_home INTEGER DEFAULT -1,  -- BFS depth
    parent_screen_id TEXT,
    FOREIGN KEY (parent_screen_id) REFERENCES screens(id) ON DELETE SET NULL
);

-- Hash mapping for known equivalent screens (different routes to same screen)
CREATE TABLE IF NOT EXISTS screen_hash_mappings (
    content_hash TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- UI Elements within screens
CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    
    -- Element identification
    element_type TEXT NOT NULL,  -- raw type from accessibility
    normalized_type TEXT,         -- normalized (button, input, etc.)
    semantic_type TEXT,          -- AI-assigned meaning (add_to_cart_button)
    
    -- Content
    label TEXT DEFAULT '',
    text_content TEXT DEFAULT '',
    hint TEXT DEFAULT '',
    accessibility_id TEXT DEFAULT '',
    resource_id TEXT DEFAULT '',
    
    -- Position
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    -- center_x and center_y are calculated in code, not stored
    
    -- Properties
    enabled INTEGER DEFAULT 1,
    clickable INTEGER DEFAULT 0,
    focusable INTEGER DEFAULT 0,
    checked INTEGER DEFAULT 0,
    confidence REAL DEFAULT 1.0,
    
    -- Interaction tracking
    interacted INTEGER DEFAULT 0,
    interaction_count INTEGER DEFAULT 0,
    interaction_result TEXT DEFAULT '',  -- success, error, no_change, etc.
    last_interaction_time REAL,
    
    -- AI analysis
    purpose TEXT DEFAULT '',  -- What this element does
    is_primary_action INTEGER DEFAULT 0,
    
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- Screen transitions (navigation graph)
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_screen_id TEXT NOT NULL,
    to_screen_id TEXT,  -- Can be NULL if destination not yet discovered
    element_id TEXT,    -- Element that triggered the transition
    
    -- Action details
    action_type TEXT NOT NULL,  -- tap, swipe, type, back, etc.
    action_detail TEXT DEFAULT '',  -- JSON with coordinates, text input, etc.
    
    -- Transition properties
    timestamp REAL NOT NULL,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER,  -- How long the transition took
    
    -- Navigation metadata
    is_back_navigation INTEGER DEFAULT 0,  -- If this was a back button press
    is_modal_dismiss INTEGER DEFAULT 0,    -- If this dismissed a modal
    FOREIGN KEY (from_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (to_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE SET NULL
);

-- Navigation paths (pre-computed shortest paths)
CREATE TABLE IF NOT EXISTS navigation_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_screen_id TEXT NOT NULL,
    to_screen_id TEXT NOT NULL,
    path_json TEXT NOT NULL,  -- JSON array of screen IDs
    action_sequence TEXT,     -- JSON array of actions to take
    distance INTEGER,         -- Number of steps
    created_at REAL,
    FOREIGN KEY (from_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (to_screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- User stories (test scenarios)
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    priority TEXT DEFAULT 'medium',  -- high, medium, low
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    steps_json TEXT DEFAULT '[]'
);

-- Story execution runs
CREATE TABLE IF NOT EXISTS story_executions (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    started_at REAL,
    completed_at REAL,
    duration_ms INTEGER,
    
    -- Results
    success INTEGER,  -- 1 = all passed, 0 = some failed, NULL = not finished
    passed_steps INTEGER DEFAULT 0,
    failed_steps INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    
    -- Metadata
    triggered_by TEXT DEFAULT 'manual',  -- manual, scheduled, ci
    environment TEXT,  -- device info, app version, etc.
    
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
);

-- Story execution steps (detailed results)
CREATE TABLE IF NOT EXISTS execution_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    
    -- Step definition
    action_type TEXT NOT NULL,  -- navigate, tap, type, assert, swipe
    target_screen_id TEXT,
    target_element_id TEXT,
    action_data TEXT,  -- JSON with parameters
    expected_result TEXT,
    
    -- Execution results
    status TEXT DEFAULT 'pending',  -- pending, running, passed, failed, skipped
    started_at REAL,
    completed_at REAL,
    duration_ms INTEGER,
    
    -- Actual results
    actual_screen_id TEXT,  -- Screen we were on after action
    screenshot_path TEXT,   -- Screenshot after step
    error_message TEXT,
    error_screenshot_path TEXT,
    
    -- Assertions
    assertion_passed INTEGER,
    assertion_details TEXT,
    
    FOREIGN KEY (execution_id) REFERENCES story_executions(id) ON DELETE CASCADE,
    FOREIGN KEY (target_screen_id) REFERENCES screens(id) ON DELETE SET NULL,
    FOREIGN KEY (actual_screen_id) REFERENCES screens(id) ON DELETE SET NULL
);

-- Exploration log
CREATE TABLE IF NOT EXISTS exploration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    screen_id TEXT,
    element_id TEXT,
    detail TEXT DEFAULT '',
    timestamp REAL NOT NULL
);

-- AI analysis cache (to avoid re-analyzing same screens)
CREATE TABLE IF NOT EXISTS ai_analysis_cache (
    perceptual_hash TEXT PRIMARY KEY,
    screen_type TEXT,
    name TEXT,
    description TEXT,
    confidence REAL,
    key_elements_json TEXT,
    suggested_actions_json TEXT,
    is_modal INTEGER DEFAULT 0,
    is_error_state INTEGER DEFAULT 0,
    requires_auth INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_used REAL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_screens_content_hash ON screens(content_hash);
CREATE INDEX IF NOT EXISTS idx_screens_perceptual_hash ON screens(perceptual_hash);
CREATE INDEX IF NOT EXISTS idx_screens_structure_hash ON screens(structure_hash);
CREATE INDEX IF NOT EXISTS idx_screens_type ON screens(screen_type);
CREATE INDEX IF NOT EXISTS idx_elements_screen ON elements(screen_id);
CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(element_type);
CREATE INDEX IF NOT EXISTS idx_elements_interacted ON elements(interacted);
CREATE INDEX IF NOT EXISTS idx_transitions_from ON transitions(from_screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON transitions(to_screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_element ON transitions(element_id);
CREATE INDEX IF NOT EXISTS idx_story_executions_story ON story_executions(story_id);
CREATE INDEX IF NOT EXISTS idx_execution_steps_execution ON execution_steps(execution_id);
CREATE INDEX IF NOT EXISTS idx_navigation_paths_from ON navigation_paths(from_screen_id);
CREATE INDEX IF NOT EXISTS idx_navigation_paths_to ON navigation_paths(to_screen_id);
"""


class Database:
    """Async database manager."""
    
    def __init__(self, db_path: str = "./storage/agent.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[Any] = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Initialize database connection."""
        if aiosqlite is None:
            raise RuntimeError("aiosqlite not installed")
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._connection.executescript(SCHEMA)
        await self._connection.commit()
    
    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, sql: str, parameters: tuple = ()) -> Any:
        """Execute SQL query."""
        async with self._lock:
            return await self._connection.execute(sql, parameters)
    
    async def executemany(self, sql: str, parameters: List[tuple]) -> Any:
        """Execute SQL query with multiple parameters."""
        async with self._lock:
            return await self._connection.executemany(sql, parameters)
    
    async def fetchone(self, sql: str, parameters: tuple = ()) -> Optional[Dict]:
        """Fetch single row."""
        async with self._lock:
            async with self._connection.execute(sql, parameters) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def fetchall(self, sql: str, parameters: tuple = ()) -> List[Dict]:
        """Fetch all rows."""
        async with self._lock:
            async with self._connection.execute(sql, parameters) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def commit(self):
        """Commit transaction."""
        await self._connection.commit()
    
    # === Helper methods for common operations ===
    
    async def get_screen_by_hash(self, content_hash: str) -> Optional[Dict]:
        """Get screen by its content hash."""
        return await self.fetchone(
            "SELECT * FROM screens WHERE content_hash = ?",
            (content_hash,)
        )
    
    async def get_screens_by_perceptual_hash(self, phash: str, threshold: float = 0.95) -> List[Dict]:
        """Get screens with similar perceptual hashes."""
        # This is a simple implementation - could be optimized with Hamming distance in SQL
        return await self.fetchall(
            "SELECT * FROM screens WHERE perceptual_hash IS NOT NULL"
        )
    
    async def update_screen_visit(self, screen_id: str):
        """Update visit count and last_seen for a screen."""
        import time
        await self.execute(
            """UPDATE screens 
               SET visit_count = visit_count + 1, last_seen = ? 
               WHERE id = ?""",
            (time.time(), screen_id)
        )
        await self.commit()
    
    async def mark_element_interacted(
        self, 
        element_id: str, 
        result: str = "success",
        success: bool = True
    ):
        """Mark an element as interacted with."""
        import time
        await self.execute(
            """UPDATE elements 
               SET interacted = 1, 
                   interaction_count = interaction_count + 1,
                   interaction_result = ?,
                   last_interaction_time = ?
               WHERE id = ?""",
            (result, time.time(), element_id)
        )
        await self.commit()
    
    async def record_transition(
        self,
        from_screen_id: str,
        to_screen_id: Optional[str],
        element_id: Optional[str],
        action_type: str,
        action_detail: Dict,
        duration_ms: Optional[int] = None,
        success: bool = True
    ) -> int:
        """Record a screen transition and return the transition ID."""
        import time
        cursor = await self.execute(
            """INSERT INTO transitions 
               (from_screen_id, to_screen_id, element_id, action_type, 
                action_detail, timestamp, success, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (from_screen_id, to_screen_id, element_id, action_type,
             json.dumps(action_detail), time.time(), 1 if success else 0, duration_ms)
        )
        await self.commit()
        return cursor.lastrowid
    
    async def update_transition_destination(
        self, 
        transition_id: int, 
        to_screen_id: str
    ):
        """Update the destination screen of a transition."""
        await self.execute(
            "UPDATE transitions SET to_screen_id = ? WHERE id = ?",
            (to_screen_id, transition_id)
        )
        await self.commit()
    
    async def get_untapped_elements(self, screen_id: str) -> List[Dict]:
        """Get interactive elements that haven't been tapped yet."""
        return await self.fetchall(
            """SELECT * FROM elements 
               WHERE screen_id = ? 
                 AND interacted = 0
                 AND (clickable = 1 OR element_type IN ('button', 'input', 'clickable'))
               ORDER BY is_primary_action DESC, y, x""",
            (screen_id,)
        )
    
    async def get_screen_elements(self, screen_id: str) -> List[Dict]:
        """Get all elements for a screen."""
        return await self.fetchall(
            "SELECT * FROM elements WHERE screen_id = ? ORDER BY y, x",
            (screen_id,)
        )
    
    async def get_incoming_transitions(self, screen_id: str) -> List[Dict]:
        """Get all transitions that lead to this screen."""
        return await self.fetchall(
            "SELECT * FROM transitions WHERE to_screen_id = ?",
            (screen_id,)
        )
    
    async def get_outgoing_transitions(self, screen_id: str) -> List[Dict]:
        """Get all transitions from this screen."""
        return await self.fetchall(
            "SELECT * FROM transitions WHERE from_screen_id = ?",
            (screen_id,)
        )
    
    async def create_story_execution(
        self, 
        execution_id: str, 
        story_id: str,
        total_steps: int,
        triggered_by: str = "manual",
        environment: Optional[str] = None
    ):
        """Create a new story execution record."""
        import time
        await self.execute(
            """INSERT INTO story_executions 
               (id, story_id, status, started_at, total_steps, triggered_by, environment)
               VALUES (?, ?, 'running', ?, ?, ?, ?)""",
            (execution_id, story_id, time.time(), total_steps, triggered_by, environment)
        )
        await self.commit()
    
    async def update_story_execution(
        self,
        execution_id: str,
        status: str,
        success: Optional[bool] = None,
        passed_steps: int = 0,
        failed_steps: int = 0
    ):
        """Update story execution status."""
        import time
        success_val = 1 if success else 0 if success is not None else None
        await self.execute(
            """UPDATE story_executions 
               SET status = ?, success = ?, passed_steps = ?, failed_steps = ?, completed_at = ?
               WHERE id = ?""",
            (status, success_val, passed_steps, failed_steps, time.time(), execution_id)
        )
        await self.commit()
    
    async def create_execution_step(
        self,
        execution_id: str,
        step_number: int,
        action_type: str,
        target_screen_id: Optional[str] = None,
        target_element_id: Optional[str] = None,
        action_data: Optional[Dict] = None,
        expected_result: Optional[str] = None
    ) -> int:
        """Create an execution step record."""
        import time
        cursor = await self.execute(
            """INSERT INTO execution_steps 
               (execution_id, step_number, action_type, target_screen_id, 
                target_element_id, action_data, expected_result, status, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)""",
            (execution_id, step_number, action_type, target_screen_id,
             target_element_id, 
             json.dumps(action_data) if action_data else None,
             expected_result, time.time())
        )
        await self.commit()
        return cursor.lastrowid
    
    async def complete_execution_step(
        self,
        step_id: int,
        status: str,
        actual_screen_id: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        error_message: Optional[str] = None,
        assertion_passed: Optional[bool] = None,
        assertion_details: Optional[str] = None
    ):
        """Mark an execution step as complete."""
        import time
        await self.execute(
            """UPDATE execution_steps 
               SET status = ?, completed_at = ?, actual_screen_id = ?, 
                   screenshot_path = ?, error_message = ?,
                   assertion_passed = ?, assertion_details = ?
               WHERE id = ?""",
            (status, time.time(), actual_screen_id, screenshot_path,
             error_message,
             1 if assertion_passed else 0 if assertion_passed is not None else None,
             assertion_details, step_id)
        )
        await self.commit()


# Global database instance
db = Database()
