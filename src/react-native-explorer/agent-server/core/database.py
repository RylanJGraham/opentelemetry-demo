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


SCHEMA = """
-- Screens discovered during exploration
CREATE TABLE IF NOT EXISTS screens (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    screen_type TEXT DEFAULT 'unknown',
    description TEXT DEFAULT '',
    screenshot_path TEXT,
    element_count INTEGER DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    visit_count INTEGER DEFAULT 1,
    fully_explored INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'  -- JSON blob for extensibility
);

-- UI Elements within screens
CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    element_type TEXT NOT NULL,
    label TEXT DEFAULT '',
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    interacted INTEGER DEFAULT 0,
    interaction_result TEXT DEFAULT '',
    confidence REAL DEFAULT 1.0,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- Screen transitions (navigation graph)
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_screen_id TEXT NOT NULL,
    to_screen_id TEXT,  -- Can be NULL if destination unknown yet
    element_id TEXT,
    action_type TEXT NOT NULL,
    action_detail TEXT DEFAULT '',
    timestamp REAL NOT NULL,
    FOREIGN KEY (from_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (to_screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- User stories
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    tags TEXT DEFAULT '[]',
    steps_json TEXT DEFAULT '[]'
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_elements_screen ON elements(screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_from ON transitions(from_screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON transitions(to_screen_id);
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


# Global database instance
db = Database()
