-- 0007: attorney questions
CREATE TABLE IF NOT EXISTS attorney_questions (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  question TEXT NOT NULL,
  lesson_id TEXT,
  character TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (journey_id, question)
);
