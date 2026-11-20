CREATE TABLE IF NOT EXISTS content_versions (
  entry_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  kind TEXT NOT NULL,
  body_json TEXT NOT NULL,
  state TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  submitted_by TEXT,
  submitted_at TEXT,
  published_by TEXT,
  published_at TEXT,
  PRIMARY KEY (entry_id, version)
)
