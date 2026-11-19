-- 0010: Tus datos answers and audit (T5-05)
CREATE TABLE IF NOT EXISTS datos_answers (
  journey_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  status TEXT NOT NULL,
  answer TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (journey_id, question_id)
);

CREATE TABLE IF NOT EXISTS datos_audit (
  id TEXT PRIMARY KEY,
  journey_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  old_status TEXT,
  old_answer TEXT,
  new_status TEXT NOT NULL,
  new_answer TEXT,
  actor TEXT NOT NULL,
  at TEXT NOT NULL
);
