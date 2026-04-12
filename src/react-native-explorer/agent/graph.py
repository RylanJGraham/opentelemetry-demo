"""
Enhanced Screen graph data model and SQLite persistence.
Stores screens, elements, transitions, clusters, and user stories.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import logging

logger = logging.getLogger("explorer.graph")

# Enhanced schema with screen clusters, element relationships, and stories
SCHEMA = """
-- Core screens table with enhanced metadata
CREATE TABLE IF NOT EXISTS screens (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    screen_type TEXT DEFAULT 'unknown',
    description TEXT DEFAULT '',
    screenshot_path TEXT,
    element_count INTEGER DEFAULT 0,
    cluster_id TEXT DEFAULT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    visit_count INTEGER DEFAULT 1,
    fully_explored INTEGER DEFAULT 0,
    phash TEXT DEFAULT '',
    content_hash TEXT DEFAULT '',
    structure_hash TEXT DEFAULT '',
    x INTEGER DEFAULT 0,
    y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0
);

-- UI Elements within screens
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
    confidence REAL DEFAULT 1.0,
    text_content TEXT DEFAULT '',
    accessibility_id TEXT DEFAULT '',
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- Screen transitions (navigation graph)
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_screen_id TEXT NOT NULL,
    element_id TEXT,
    to_screen_id TEXT,  -- Can be NULL if destination not yet known
    action_type TEXT NOT NULL,
    action_detail TEXT DEFAULT '',
    timestamp REAL NOT NULL,
    FOREIGN KEY (from_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (to_screen_id) REFERENCES screens(id) ON DELETE CASCADE,
    FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE SET NULL
);

-- Screen clusters (groups of similar screens)
CREATE TABLE IF NOT EXISTS clusters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    screen_type TEXT DEFAULT 'unknown',
    representative_screen_id TEXT,
    screen_count INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

-- User stories / E2E test scenarios
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    tags TEXT DEFAULT '[]',
    priority TEXT DEFAULT 'medium',
    exported_format TEXT DEFAULT ''
);

-- Story steps (actions in a story)
CREATE TABLE IF NOT EXISTS story_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    screen_id TEXT,
    element_id TEXT,
    coordinates TEXT DEFAULT '',
    data TEXT DEFAULT '',
    assertion TEXT DEFAULT '',
    screenshot_path TEXT DEFAULT '',
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE SET NULL,
    FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE SET NULL
);

-- Exploration log
CREATE TABLE IF NOT EXISTS exploration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    screen_id TEXT,
    element_id TEXT,
    detail TEXT DEFAULT '',
    timestamp REAL NOT NULL,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE SET NULL
);

-- Screen content/features detected
CREATE TABLE IF NOT EXISTS screen_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    feature_value TEXT DEFAULT '',
    confidence REAL DEFAULT 1.0,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_elements_screen ON elements(screen_id);
CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(element_type);
CREATE INDEX IF NOT EXISTS idx_transitions_from ON transitions(from_screen_id);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON transitions(to_screen_id);
CREATE INDEX IF NOT EXISTS idx_screens_cluster ON screens(cluster_id);
CREATE INDEX IF NOT EXISTS idx_screens_phash ON screens(phash);
CREATE INDEX IF NOT EXISTS idx_screens_structure ON screens(structure_hash);
CREATE INDEX IF NOT EXISTS idx_story_steps_story ON story_steps(story_id);
CREATE INDEX IF NOT EXISTS idx_screen_features_screen ON screen_features(screen_id);
"""


class ScreenGraph:
    """Enhanced async SQLite-backed screen graph with clustering and story support."""

    def __init__(self, db_path: str = "./storage/graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Open database connection and create tables."""
        # Check if we need to migrate (before connecting)
        await self._migrate_if_needed()
        
        # 🔧 Use 5.0s timeout to avoid indefinite hanging on Windows if file is locked
        self._db = await aiosqlite.connect(str(self.db_path), timeout=5.0)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def _migrate_if_needed(self):
        """Handle schema migrations by checking current schema version."""
        if not self.db_path.exists():
            return  # New database, no migration needed
            
        # Quick check: try to connect and see if schema is compatible
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("PRAGMA table_info(screens)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            required_columns = {"cluster_id", "phash", "content_hash", "structure_hash"}
            
            if columns and not required_columns.issubset(columns):
                # Schema is outdated, need to migrate
                logger.warning("Database schema outdated. Backing up and recreating...")
                self._backup_and_recreate()
        except Exception as e:
            # Table might not exist yet, which is fine
            pass

    def _backup_and_recreate(self):
        """Backup old data and recreate with new schema."""
        import shutil
        from datetime import datetime
        
        # Backup old database
        backup_path = self.db_path.parent / f"graph_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(self.db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        
        # Delete old database
        self.db_path.unlink()
        logger.info("Old database removed. Will create fresh database with new schema.")

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def clear(self):
        """Wipe all graph data from the database."""
        if not self._db:
            return
        await self._db.execute("DELETE FROM exploration_log")
        await self._db.execute("DELETE FROM story_steps")
        await self._db.execute("DELETE FROM stories")
        await self._db.execute("DELETE FROM transitions")
        await self._db.execute("DELETE FROM elements")
        await self._db.execute("DELETE FROM screen_features")
        await self._db.execute("DELETE FROM screens")
        await self._db.execute("DELETE FROM clusters")
        await self._db.commit()

    # ── Screens ──────────────────────────────────────────────────────

    async def add_screen(
        self,
        screen_id: str,
        name: str,
        screen_type: str = "unknown",
        description: str = "",
        screenshot_path: str = "",
        element_count: int = 0,
        phash: str = "",
        content_hash: str = "",
        structure_hash: str = "",
        dimensions: dict = None,
    ) -> str:
        """Insert a new screen or update visit count if it already exists."""
        now = time.time()
        existing = await self.get_screen(screen_id)
        if existing:
            await self._db.execute(
                """UPDATE screens SET 
                   last_seen = ?, visit_count = visit_count + 1
                   WHERE id = ?""",
                (now, screen_id),
            )
        else:
            dims = dimensions or {}
            await self._db.execute(
                """INSERT INTO screens 
                   (id, name, screen_type, description, screenshot_path,
                    element_count, phash, content_hash, structure_hash,
                    first_seen, last_seen, x, y, width, height)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (screen_id, name, screen_type, description, screenshot_path,
                 element_count, phash, content_hash, structure_hash,
                 now, now, dims.get("x", 0), dims.get("y", 0),
                 dims.get("width", 0), dims.get("height", 0)),
            )
        await self._db.commit()
        return screen_id

    async def get_screen(self, screen_id: str) -> Optional[dict]:
        """Get a screen by ID."""
        if not self._db:
            return None
        async with self._db.execute("SELECT * FROM screens WHERE id = ?", (screen_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_screen_by_hash(self, content_hash: str) -> Optional[dict]:
        """Find a screen by its content hash."""
        async with self._db.execute(
            "SELECT * FROM screens WHERE content_hash = ?", (content_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_screens_by_phash(self, phash: str, threshold: int = 5) -> list[dict]:
        """Find screens with similar perceptual hashes using Hamming distance.
        
        Instead of exact string match, loads all screen phashes and compares
        using bit-level Hamming distance. Threshold of 5 means ~10% bit
        difference is tolerated (handles animation states, keyboards, etc).
        """
        if not self._db or not phash:
            return []
        
        # First try exact match (fast path)
        async with self._db.execute(
            "SELECT * FROM screens WHERE phash = ?", (phash,)
        ) as cursor:
            rows = await cursor.fetchall()
            if rows:
                return [dict(r) for r in rows]
        
        # Fuzzy match: load all phashes and compare with Hamming distance
        async with self._db.execute(
            "SELECT id, phash FROM screens WHERE phash IS NOT NULL AND phash != ''"
        ) as cursor:
            candidates = await cursor.fetchall()
        
        matching_ids = []
        for row in candidates:
            try:
                candidate_phash = row["phash"]
                if len(candidate_phash) != len(phash):
                    continue
                # Compute Hamming distance
                xor_val = int(phash, 16) ^ int(candidate_phash, 16)
                dist = bin(xor_val).count('1')
                if dist <= threshold:
                    matching_ids.append(row["id"])
            except (ValueError, TypeError):
                continue
        
        if not matching_ids:
            return []
        
        # Fetch full screen data for matches
        placeholders = ",".join("?" for _ in matching_ids)
        async with self._db.execute(
            f"SELECT * FROM screens WHERE id IN ({placeholders})", matching_ids
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_screens(self, cluster_id: str = None) -> list[dict]:
        """Get all screens, optionally filtered by cluster."""
        if not self._db:
            return []
        if cluster_id:
            async with self._db.execute(
                "SELECT * FROM screens WHERE cluster_id = ? ORDER BY first_seen",
                (cluster_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with self._db.execute(
                "SELECT * FROM screens ORDER BY first_seen"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_screen_count(self) -> int:
        """Get total number of screens."""
        if not self._db:
            return 0
        async with self._db.execute("SELECT COUNT(*) as cnt FROM screens") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_transition_count(self) -> int:
        """Get total number of transitions."""
        if not self._db:
            return 0
        async with self._db.execute("SELECT COUNT(*) as cnt FROM transitions") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def mark_screen_explored(self, screen_id: str):
        """Mark a screen as fully explored."""
        await self._db.execute(
            "UPDATE screens SET fully_explored = 1 WHERE id = ?", (screen_id,)
        )
        await self._db.commit()

    async def update_screen_cluster(self, screen_id: str, cluster_id: str):
        """Assign a screen to a cluster."""
        await self._db.execute(
            "UPDATE screens SET cluster_id = ? WHERE id = ?", (cluster_id, screen_id)
        )
        await self._db.commit()

    async def search_screens(self, query: str) -> list[dict]:
        """Search screens by name, description, or type."""
        search_term = f"%{query}%"
        async with self._db.execute(
            """SELECT * FROM screens 
               WHERE name LIKE ? OR description LIKE ? OR screen_type LIKE ?
               ORDER BY first_seen""",
            (search_term, search_term, search_term),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

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
        text_content: str = "",
        accessibility_id: str = "",
        confidence: float = 1.0,
    ) -> str:
        """Insert a new UI element for a screen."""
        await self._db.execute(
            """INSERT OR REPLACE INTO elements
               (id, screen_id, element_type, label, description, x, y, width, height,
                text_content, accessibility_id, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (element_id, screen_id, element_type, label, description, x, y, width, height,
             text_content, accessibility_id, confidence),
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

    async def get_untried_actions(self, screen_id: str) -> list[dict]:
        """Alias for get_unexplored_elements for compatibility with the Explorer loop."""
        return await self.get_unexplored_elements(screen_id)

    async def mark_element_interacted(self, element_id: str, result: str = ""):
        """Mark an element as interacted."""
        await self._db.execute(
            "UPDATE elements SET interacted = 1, interaction_result = ? WHERE id = ?",
            (result, element_id),
        )
        await self._db.commit()

    async def mark_action_tried(self, element_id: str, result: str = ""):
        """Alias for mark_element_interacted for compatibility with the Explorer loop."""
        return await self.mark_element_interacted(element_id, result)

    async def get_elements_by_type(self, element_type: str) -> list[dict]:
        """Get all elements of a specific type across all screens."""
        async with self._db.execute(
            "SELECT * FROM elements WHERE element_type = ? ORDER BY screen_id, y, x",
            (element_type,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Transitions ──────────────────────────────────────────────────

    async def add_transition(
        self,
        from_screen_id: str,
        to_screen_id: Optional[str],
        action_type: str,
        element_id: Optional[str] = None,
        action_detail: str = "",
    ) -> int:
        """Record a screen transition."""
        if not self._db:
            raise RuntimeError("Database not connected. Call connect() first.")
        now = time.time()
        # Serialize action_detail if it's a dict
        if isinstance(action_detail, dict):
            action_detail = json.dumps(action_detail)
        cursor = await self._db.execute(
            """INSERT INTO transitions (from_screen_id, element_id, to_screen_id,
               action_type, action_detail, timestamp) VALUES (?, ?, ?, ?, ?, ?)""",
            (from_screen_id, element_id, to_screen_id, action_type, action_detail, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_transitions_from(self, screen_id: str) -> list[dict]:
        """Get all transitions from a screen."""
        if not self._db:
            return []
        async with self._db.execute(
            "SELECT * FROM transitions WHERE from_screen_id = ?", (screen_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_transitions_to(self, screen_id: str) -> list[dict]:
        """Get all transitions to a screen."""
        async with self._db.execute(
            "SELECT * FROM transitions WHERE to_screen_id = ?", (screen_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_transitions(self) -> list[dict]:
        """Get all transitions."""
        if not self._db:
            return []
        async with self._db.execute("SELECT * FROM transitions ORDER BY timestamp") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_transition_target(self, transition_id: int, to_screen_id: str):
        """Update a transition's target screen (fixes orphan transitions)."""
        if not self._db:
            return
        await self._db.execute(
            "UPDATE transitions SET to_screen_id = ? WHERE id = ? AND to_screen_id IS NULL",
            (to_screen_id, transition_id),
        )
        await self._db.commit()

    async def get_shortest_path(self, from_screen_id: str, to_screen_id: str) -> list[str]:
        """Find shortest path between two screens using BFS."""
        if from_screen_id == to_screen_id:
            return [from_screen_id]
        
        visited = {from_screen_id}
        queue = [(from_screen_id, [from_screen_id])]
        
        while queue:
            current, path = queue.pop(0)
            transitions = await self.get_transitions_from(current)
            
            for t in transitions:
                next_screen = t["to_screen_id"]
                if next_screen == to_screen_id:
                    return path + [next_screen]
                if next_screen not in visited:
                    visited.add(next_screen)
                    queue.append((next_screen, path + [next_screen]))
        
        return []  # No path found

    # ── Clusters ─────────────────────────────────────────────────────

    async def create_cluster(
        self,
        cluster_id: str,
        name: str,
        description: str = "",
        screen_type: str = "unknown",
        representative_screen_id: str = None,
    ) -> str:
        """Create a new screen cluster."""
        now = time.time()
        await self._db.execute(
            """INSERT OR REPLACE INTO clusters
               (id, name, description, screen_type, representative_screen_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cluster_id, name, description, screen_type, representative_screen_id, now),
        )
        await self._db.commit()
        return cluster_id

    async def get_clusters(self) -> list[dict]:
        """Get all clusters with screen counts."""
        if not self._db:
            return []
        async with self._db.execute(
            """SELECT c.*, COUNT(s.id) as screen_count 
               FROM clusters c
               LEFT JOIN screens s ON c.id = s.cluster_id
               GROUP BY c.id"""
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def auto_cluster_screens(self):
        """Automatically cluster screens by type."""
        async with self._db.execute(
            "SELECT DISTINCT screen_type FROM screens WHERE cluster_id IS NULL"
        ) as cursor:
            types = await cursor.fetchall()
        
        for row in types:
            screen_type = row["screen_type"]
            cluster_id = f"cluster_{screen_type}"
            await self.create_cluster(
                cluster_id=cluster_id,
                name=f"{screen_type.title()} Screens",
                screen_type=screen_type,
            )
            await self._db.execute(
                "UPDATE screens SET cluster_id = ? WHERE screen_type = ? AND cluster_id IS NULL",
                (cluster_id, screen_type),
            )
        await self._db.commit()

    # ── Stories ──────────────────────────────────────────────────────

    async def create_story(
        self,
        story_id: str,
        name: str,
        description: str = "",
        tags: list = None,
        priority: str = "medium",
    ) -> str:
        """Create a new user story."""
        now = time.time()
        await self._db.execute(
            """INSERT INTO stories (id, name, description, created_at, updated_at, tags, priority)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (story_id, name, description, now, now, json.dumps(tags or []), priority),
        )
        await self._db.commit()
        return story_id

    async def get_stories(self) -> list[dict]:
        """Get all stories with step counts."""
        if not self._db:
            return []
        async with self._db.execute(
            """SELECT s.*, COUNT(ss.id) as step_count
               FROM stories s
               LEFT JOIN story_steps ss ON s.id = ss.story_id
               GROUP BY s.id
               ORDER BY s.created_at DESC"""
        ) as cursor:
            rows = await cursor.fetchall()
            stories = []
            for r in rows:
                story = dict(r)
                story["tags"] = json.loads(story.get("tags", "[]"))
                stories.append(story)
            return stories

    async def get_story(self, story_id: str) -> Optional[dict]:
        """Get a story with all its steps."""
        async with self._db.execute(
            "SELECT * FROM stories WHERE id = ?", (story_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            story = dict(row)
            story["tags"] = json.loads(story.get("tags", "[]"))
        
        async with self._db.execute(
            "SELECT * FROM story_steps WHERE story_id = ? ORDER BY step_number",
            (story_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            story["steps"] = [dict(r) for r in rows]
        
        return story

    async def add_story_step(
        self,
        story_id: str,
        step_number: int,
        action_type: str,
        screen_id: str = None,
        element_id: str = None,
        coordinates: tuple = None,
        data: dict = None,
        assertion: str = "",
        screenshot_path: str = "",
    ) -> int:
        """Add a step to a story."""
        coord_str = json.dumps(coordinates) if coordinates else ""
        data_str = json.dumps(data) if data else ""
        
        cursor = await self._db.execute(
            """INSERT INTO story_steps 
               (story_id, step_number, action_type, screen_id, element_id, 
                coordinates, data, assertion, screenshot_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (story_id, step_number, action_type, screen_id, element_id,
             coord_str, data_str, assertion, screenshot_path),
        )
        
        # Update story updated_at
        await self._db.execute(
            "UPDATE stories SET updated_at = ? WHERE id = ?",
            (time.time(), story_id),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def delete_story(self, story_id: str):
        """Delete a story and all its steps."""
        await self._db.execute("DELETE FROM story_steps WHERE story_id = ?", (story_id,))
        await self._db.execute("DELETE FROM stories WHERE id = ?", (story_id,))
        await self._db.commit()

    async def update_story_export(self, story_id: str, format_name: str):
        """Record that a story was exported to a specific format."""
        await self._db.execute(
            "UPDATE stories SET exported_format = ? WHERE id = ?",
            (format_name, story_id),
        )
        await self._db.commit()

    # ── Screen Features ──────────────────────────────────────────────

    async def add_screen_feature(
        self, screen_id: str, feature_type: str, feature_value: str = "", confidence: float = 1.0
    ):
        """Add a detected feature to a screen (e.g., 'has_form', 'has_list')."""
        await self._db.execute(
            """INSERT INTO screen_features (screen_id, feature_type, feature_value, confidence)
               VALUES (?, ?, ?, ?)""",
            (screen_id, feature_type, feature_value, confidence),
        )
        await self._db.commit()

    async def get_screen_features(self, screen_id: str) -> list[dict]:
        """Get all features for a screen."""
        async with self._db.execute(
            "SELECT * FROM screen_features WHERE screen_id = ?", (screen_id,)
        ) as cursor:
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
        if not self._db:
            return {"nodes": [], "edges": [], "clusters": [], "stats": {"total_screens": 0, "total_transitions": 0, "total_clusters": 0, "explored_screens": 0}}
        screens = await self.get_all_screens()
        transitions = await self.get_all_transitions()
        clusters = await self.get_clusters()

        # Build nodes with elements and features
        nodes = []
        for s in screens:
            elements = await self.get_elements_for_screen(s["id"])
            features = await self.get_screen_features(s["id"])
            nodes.append({
                **s,
                "elements": elements,
                "features": features,
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
            "clusters": clusters,
            "stats": {
                "total_screens": len(screens),
                "total_transitions": len(transitions),
                "total_clusters": len(clusters),
                "explored_screens": sum(1 for s in screens if s["fully_explored"]),
            },
        }

    async def export_for_e2e(self) -> dict:
        """Export data in a format suitable for E2E test generation."""
        screens = await self.get_all_screens()
        stories = await self.get_stories()
        
        return {
            "app_name": "React Native App",
            "exported_at": datetime.now().isoformat(),
            "screens": screens,
            "user_stories": stories,
            "screen_count": len(screens),
            "story_count": len(stories),
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
