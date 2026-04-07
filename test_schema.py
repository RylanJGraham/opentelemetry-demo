import sqlite3

schema = '''
-- Screens discovered during exploration
CREATE TABLE IF NOT EXISTS screens (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    screen_type TEXT DEFAULT 'unknown',
    description TEXT DEFAULT '',
    screenshot_path TEXT,
    content_hash TEXT UNIQUE,
    perceptual_hash TEXT,
    structure_hash TEXT,
    element_structure_hash TEXT,
    element_count INTEGER DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    visit_count INTEGER DEFAULT 1,
    fully_explored INTEGER DEFAULT 0,
    ai_confidence REAL DEFAULT 0.0,
    is_modal INTEGER DEFAULT 0,
    is_error_state INTEGER DEFAULT 0,
    requires_auth INTEGER DEFAULT 0,
    ai_metadata TEXT DEFAULT '{}',
    depth_from_home INTEGER DEFAULT -1,
    parent_screen_id TEXT,
    FOREIGN KEY (parent_screen_id) REFERENCES screens(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS screen_hash_mappings (
    content_hash TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    screen_id TEXT NOT NULL,
    element_type TEXT NOT NULL,
    normalized_type TEXT,
    semantic_type TEXT,
    label TEXT DEFAULT '',
    text_content TEXT DEFAULT '',
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    clickable INTEGER DEFAULT 0,
    FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_screens_content_hash ON screens(content_hash);
'''

conn = sqlite3.connect(':memory:')
try:
    conn.executescript(schema)
    print('Schema OK!')
except Exception as e:
    print(f'Error: {e}')
