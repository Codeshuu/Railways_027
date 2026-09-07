-- schema.sql
-- Indian Railways Automatic Block Planning Database Schema (Weekly Scope)

CREATE TABLE IF NOT EXISTS defects (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    corridor_id TEXT NOT NULL,
    defect_type TEXT NOT NULL,
    severity INTEGER NOT NULL,
    date_reported TEXT NOT NULL,
    due_date TEXT NOT NULL,
    estimated_block_duration REAL NOT NULL,
    department TEXT NOT NULL,
    location_marker TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS corridors (
    corridor_id TEXT PRIMARY KEY,
    section_name TEXT NOT NULL,
    is_high_density INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corridor_id TEXT NOT NULL,
    date TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    train_count INTEGER NOT NULL,
    goods_forecast_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    corridor_id TEXT NOT NULL,
    date TEXT NOT NULL,
    slot_start TEXT NOT NULL,
    slot_end TEXT NOT NULL,
    priority_score REAL NOT NULL,
    merged_with TEXT,
    explanation_text TEXT
);
