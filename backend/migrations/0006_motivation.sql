-- 0006: motivation (petals, reminders)
CREATE TABLE IF NOT EXISTS petal_awards (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  ref TEXT NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (journey_id, reason, ref)
);

CREATE TABLE IF NOT EXISTS reminders (
  journey_id TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  local_time TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_sent_on TEXT
);

INSERT INTO settings (key, value_json, updated_by, updated_at)
VALUES ('levels', '{"aprendiz":0,"conocedor":300,"planeador":800,"guardian":1500}', 'migration', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;
