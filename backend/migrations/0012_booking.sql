-- 0012: availability, holidays, bookings (T6-07)
CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  start_utc TEXT NOT NULL,
  end_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cancelled_at TEXT
);

CREATE TABLE IF NOT EXISTS booking_blocks (
  block_start_utc TEXT PRIMARY KEY,
  booking_id TEXT NOT NULL
);
