CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    technology TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    delta_pct REAL,
    metadata TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eol_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology TEXT NOT NULL,
    version TEXT,
    eol_date DATE,
    latest_version TEXT,
    is_lts BOOLEAN,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scored_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology TEXT NOT NULL,
    total_score REAL,
    score_breakdown TEXT,
    trigger_type TEXT,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT,
    top_technologies TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- eol_events is re-collected every run; keep one row per product+version
-- so repeated runs update in place instead of accumulating duplicates.
CREATE UNIQUE INDEX IF NOT EXISTS idx_eol_unique
    ON eol_events (technology, version);

CREATE INDEX IF NOT EXISTS idx_signals_lookup
    ON signals (technology, source, collected_at);

CREATE INDEX IF NOT EXISTS idx_scored_lookup
    ON scored_signals (scored_at, total_score);
