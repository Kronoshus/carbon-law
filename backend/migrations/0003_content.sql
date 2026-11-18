-- 0003: lesson content
CREATE TABLE IF NOT EXISTS content_units (
  id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS content_sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  cite TEXT NOT NULL,
  url TEXT NOT NULL,
  read_on TEXT
);

CREATE TABLE IF NOT EXISTS content_lessons (
  id TEXT PRIMARY KEY,
  unit TEXT NOT NULL,
  day INTEGER,
  character TEXT,
  sensitive INTEGER NOT NULL DEFAULT 0,
  datos TEXT,
  title_es TEXT,
  title_en TEXT,
  position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS content_steps (
  id TEXT PRIMARY KEY,
  lesson_id TEXT NOT NULL,
  position INTEGER NOT NULL DEFAULT 0,
  title_es TEXT,
  title_en TEXT
);

CREATE TABLE IF NOT EXISTS content_items (
  id TEXT PRIMARY KEY,
  lesson_id TEXT NOT NULL,
  step_id TEXT NOT NULL,
  position INTEGER NOT NULL DEFAULT 0,
  kind TEXT NOT NULL,
  legal INTEGER NOT NULL DEFAULT 0,
  sensitive INTEGER NOT NULL DEFAULT 0,
  character TEXT,
  source_id TEXT,
  answer TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL DEFAULT 'draft',
  payload_json_es TEXT NOT NULL,
  payload_json_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_approvals (
  item_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  attorney TEXT NOT NULL,
  approved_at TEXT NOT NULL,
  PRIMARY KEY (item_id, version)
);
