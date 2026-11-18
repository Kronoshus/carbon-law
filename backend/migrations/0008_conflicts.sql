-- 0008: conflicts (firm list + per-journey checks)
CREATE TABLE IF NOT EXISTS conflict_names (
  name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS conflict_checks (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  names_json TEXT NOT NULL,
  matches_json TEXT NOT NULL,
  result TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  decided_by TEXT,
  decided_at TEXT,
  decision TEXT
);
