-- 0013: payments (T6-02/T6-03)
CREATE TABLE IF NOT EXISTS stripe_events (
  id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  paid_at TEXT NOT NULL,
  UNIQUE (journey_id, session_id)
);

CREATE TABLE IF NOT EXISTS refunds (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL
);
