-- 0015: client review of approved documents (T6-06)
CREATE TABLE IF NOT EXISTS client_reviews (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  journey_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  change_type TEXT,
  note TEXT,
  at TEXT NOT NULL
);
