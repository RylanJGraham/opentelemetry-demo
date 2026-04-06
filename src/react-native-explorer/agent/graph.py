"""
Screen graph data model and SQLite persistence.
Stores screens, elements, and transitions as a directed graph.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

SCHEMA = """
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
    fully_explored INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    element_type TEXT NOT NULL,
    label TEXT DEFAULT '',
    description TEXT DEFAULT '',
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    interacted INTEGER DEFAULT 0,
    interaction_result TEXT DEFAULT '',
    FOREIGN KEY (screen_id) REFERENCES screens(id)
);

CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_screen_id TEXT NOT NULL,
    element_id TEXT,
    to_screen_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT DEFAULT '',
    timestamp REAL NOT NULL,
    FOREIGN KEY (from_screen_id) REFERENCES screens(id),
    FOREIGN KEY (to_screen_id) REFERENCES screens(id)
);

CREATE TABLE IF NOT EXISTS exploration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    screen_id TEXT,
    element_id TEXT,
    detail TEXT DEFAULT '',
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_elements_screen ON elements(screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_from ON transitions(from_screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON transitions(to_screen_id);
"""


class ScreenGraph:
    """Async SQLite-backed screen graph for storing exploration results."""

    def __init__(self, db_path: str = "./storage/graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Open database connection and create tables."""
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ── Screens ──────────────────────────────────────────────────────

    async def add_screen(
        self,
        screen_id: str,
        name: str,
        screen_type: str = "unknown",
        description: str = "",
        screenshot_path: str = "",
        element_count: int = 0,
    ) -> str:
        """Insert a new screen or update visit count if it already exists."""
        now = time.time()
        existing = await self.get_screen(screen_id)
        if existing:
            await self._db.execute(
                """UPDATE screens SET last_seen = ?, visit_count = visit_count + 1
                   WHERE id = ?""",
                (now, screen_id),
            )
        else:
            await self._db.execute(
                """INSERT INTO screens (id, name, screen_type, description, screenshot_path,
                   element_count, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (screen_id, name, screen_type, description, screenshot_path, element_count, now, now),
            )
        await self._db.commit()
        return screen_id

    async def get_screen(self, screen_id: str) -> Optional[dict]:
        """Get a screen by ID."""
        async with self._db.execute("SELECT * FROM screens WHERE id = ?", (screen_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_screens(self) -> list[dict]:
        """Get all screens."""
        async with self._db.execute("SELECT * FROM screens ORDER BY first_seen") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_screen_count(self) -> int:
        """Get total number of screens."""
        async with self._db.execute("SELECT COUNT(*) as cnt FROM screens") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def mark_screen_explored(self, screen_id: str):
        """Mark a screen as fully explored."""
        await self._db.execute(
            "UPDATE screens SET fully_explored = 1 WHERE id = ?", (screen_id,)
        )
        await self._db.commit()

    async def update_screen_name(self, screen_id: str, name: str):
        """Update screen name (e.g., after better vision analysis)."""
        await self._db.execute(
            "UPDATE screens SET name = ? WHERE id = ?", (name, screen_id)
        )
        await self._db.commit()

    # ── Elements ─────────────────────────────────────────────────────

    async def add_element(
        self,
        element_id: str,
        screen_id: str,
        element_type: str,
        label: str = "",
        description: str = "",
        x: int = 0,
        y: int = 0,
        width: int = 0,
        height: int = 0,
    ) -> str:
        """Insert a new UI element for a screen."""
        await self._db.execute(
            """INSERT OR REPLACE INTO elements
               (id, screen_id, element_type, label, description, x, y, width, height)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (element_id, screen_id, element_type, label, description, x, y, width, height),
        )
        await self._db.commit()
        return element_id

    async def get_elements_for_screen(self, screen_id: str) -> list[dict]:
        """Get all elements for a screen."""
        async with self._db.execute(
            "SELECT * FROM elements WHERE screen_id = ? ORDER BY y, x", (screen_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_unexplored_elements(self, screen_id: str) -> list[dict]:
        """Get elements that haven't been interacted with yet."""
        async with self._db.execute(
            "SELECT * FROM elements WHERE screen_id = ? AND interacted = 0 ORDER BY y, x",
            (screen_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def mark_element_interacted(self, element_id: str, result: str = ""):
        """Mark an element as interacted."""
        await self._db.execute(
            "UPDATE elements SET interacted = 1, interaction_result = ? WHERE id = ?",
            (result, element_id),
        )
        await self._db.commit()

    # ── Transitions ──────────────────────────────────────────────────

    async def add_transition(
        self,
        from_screen_id: str,
        to_screen_id: str,
        action_type: str,
        element_id: Optional[str] = None,
        action_detail: str = "",
    ) -> int:
        """Record a screen transition."""
        now = time.time()
        cursor = await self._db.execute(
            """INSERT INTO transitions (from_screen_id, element_id, to_screen_id,
               action_type, action_detail, timestamp) VALUES (?, ?, ?, ?, ?, ?)""",
            (from_screen_id, element_id, to_screen_id, action_type, action_detail, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_transitions_from(self, screen_id: str) -> list[dict]:
        """Get all transitions from a screen."""
        async with self._db.execute(
            "SELECT * FROM transitions WHERE from_screen_id = ?", (screen_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_transitions(self) -> list[dict]:
        """Get all transitions."""
        async with self._db.execute("SELECT * FROM transitions ORDER BY timestamp") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Exploration Log ──────────────────────────────────────────────

    async def log_action(
        self, action_type: str, screen_id: str = "", element_id: str = "", detail: str = ""
    ):
        """Log an exploration action for debugging and replay."""
        now = time.time()
        await self._db.execute(
            """INSERT INTO exploration_log (action_type, screen_id, element_id, detail, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (action_type, screen_id, element_id, detail, now),
        )
        await self._db.commit()

    # ── Export ────────────────────────────────────────────────────────

    async def export_graph_json(self) -> dict:
        """Export the full graph as JSON for the web UI."""
        screens = await self.get_all_screens()
        transitions = await self.get_all_transitions()

        # Build nodes with elements
        nodes = []
        for s in screens:
            elements = await self.get_elements_for_screen(s["id"])
            nodes.append({
                **s,
                "elements": elements,
                "first_seen": s["first_seen"],
                "last_seen": s["last_seen"],
            })

        # Build edges
        edges = []
        for t in transitions:
            edges.append({
                "id": t["id"],
                "source": t["from_screen_id"],
                "target": t["to_screen_id"],
                "action_type": t["action_type"],
                "action_detail": t.get("action_detail", ""),
                "element_id": t.get("element_id"),
                "timestamp": t["timestamp"],
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_screens": len(screens),
                "total_transitions": len(transitions),
                "explored_screens": sum(1 for s in screens if s["fully_explored"]),
            },
        }

    async def get_all_paths(self, start_screen_id: str = None) -> list[list[str]]:
        """Get all unique paths through the screen graph (BFS)."""
        screens = await self.get_all_screens()
        if not screens:
            return []

        start = start_screen_id or screens[0]["id"]
        transitions = await self.get_all_transitions()

        # Build adjacency list
        adj: dict[str, list[str]] = {}
        for t in transitions:
            adj.setdefault(t["from_screen_id"], []).append(t["to_screen_id"])

        # BFS to find all paths
        paths = []
        queue = [[start]]
        visited_paths = set()

        while queue and len(paths) < 100:
            path = queue.pop(0)
            current = path[-1]

            neighbors = adj.get(current, [])
            if not neighbors:
                path_key = "->".join(path)
                if path_key not in visited_paths:
                    paths.append(path)
                    visited_paths.add(path_key)
                continue

            for neighbor in neighbors:
                if neighbor not in path:  # Avoid cycles
                    new_path = path + [neighbor]
                    queue.append(new_path)
                else:
                    path_key = "->".join(path)
                    if path_key not in visited_paths:
                        paths.append(path)
                        visited_paths.add(path_key)

        return paths
