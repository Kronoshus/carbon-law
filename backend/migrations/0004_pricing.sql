-- 0004: pricing + discounts
CREATE TABLE IF NOT EXISTS discounts (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  document TEXT NOT NULL,
  event TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  earned_at TEXT NOT NULL,
  UNIQUE (journey_id, document, event)
);

INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES
('pricing', '{"base":{"will":300000,"trust":500000,"poa":200000,"ahcd":200000},"packages":{},"discounts":{"will":{"amount":10000,"events":["lesson_completed:will","lesson_completed:trust","lesson_completed:ahcd","lesson_completed:poa","intake_completed"],"floor":250000}},"placeholder_codes":["trust","poa","ahcd"]}', 'migration', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;
