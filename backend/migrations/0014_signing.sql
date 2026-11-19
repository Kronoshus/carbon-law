-- 0014: executed (signed) documents and storage (T6-08)
CREATE TABLE IF NOT EXISTS executed_documents (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  name TEXT NOT NULL,
  filename TEXT NOT NULL,
  content_b64 TEXT NOT NULL,
  uploaded_by TEXT,
  uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
