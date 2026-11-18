-- 0005: learning attempts and lesson completions (no answer text is stored)
CREATE TABLE IF NOT EXISTS item_attempts (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  attempt INTEGER NOT NULL,
  correct INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (journey_id, item_id, attempt)
);

CREATE TABLE IF NOT EXISTS lesson_completions (
  journey_id TEXT NOT NULL,
  lesson_id TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (journey_id, lesson_id)
);

INSERT INTO settings (key, value_json, updated_by, updated_at)
VALUES ('lessons_per_day', '1', 'migration', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;
