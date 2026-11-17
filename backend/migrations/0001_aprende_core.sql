-- 0001: Aprende core tables
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_by TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS journeys (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  tz TEXT,
  started_at TEXT,
  matter_id TEXT
);

CREATE TABLE IF NOT EXISTS journey_events (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  type TEXT NOT NULL,
  payload_json TEXT,
  actor TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dedupe_key TEXT,
  UNIQUE (journey_id, type, dedupe_key)
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  key TEXT UNIQUE,
  payload_json TEXT,
  status TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  run_after TEXT,
  locked_by TEXT,
  locked_at TEXT,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS ai_calls (
  id TEXT PRIMARY KEY,
  purpose TEXT,
  model TEXT,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  latency_ms INTEGER,
  cost_usd_est REAL,
  request_sha256 TEXT,
  response_sha256 TEXT,
  ok INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  journey_id TEXT,
  type TEXT NOT NULL,
  props_json TEXT,
  target TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
