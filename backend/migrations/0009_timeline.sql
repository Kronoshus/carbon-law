-- 0009: timeline alerts
CREATE TABLE IF NOT EXISTS timeline_alerts (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  step TEXT NOT NULL,
  due TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (journey_id, step, due)
);

INSERT INTO settings (key, value_json, updated_by, updated_at)
VALUES ('turnaround', '{"conflict_bd":2,"scope_bd":2,"review_bd":3,"revise_bd":2}', 'migration', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value_json, updated_by, updated_at)
VALUES ('holidays', '[]', 'migration', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;
