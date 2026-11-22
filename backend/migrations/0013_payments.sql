-- 0013: payments (T6-02/T6-03). Stripe is the record of money, and these rows are what the app acted on.
CREATE TABLE IF NOT EXISTS checkout_sessions (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  session_id TEXT NOT NULL UNIQUE,
  amount_cents INTEGER NOT NULL,
  paid_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL
);
