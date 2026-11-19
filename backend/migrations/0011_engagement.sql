-- 0011: engagement letter templates and signatures (T6-01)
CREATE TABLE IF NOT EXISTS engagement_templates (
  id TEXT PRIMARY KEY,
  version INTEGER NOT NULL,
  es TEXT NOT NULL,
  en TEXT NOT NULL,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approved_by TEXT,
  approved_at TEXT
);

CREATE TABLE IF NOT EXISTS engagement_signatures (
  journey_id TEXT PRIMARY KEY,
  template_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  lang TEXT NOT NULL,
  text TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  client_name TEXT NOT NULL,
  client_ip TEXT,
  client_signed_at TEXT NOT NULL,
  attorney_name TEXT,
  attorney_signed_at TEXT
);
