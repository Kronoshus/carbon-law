-- 0002: characters
CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 1,
  units_json TEXT,
  voice_es TEXT,
  voice_en TEXT,
  persona_learn_id TEXT,
  persona_intake_id TEXT
);

INSERT INTO characters (id, enabled, units_json, voice_es, voice_en, persona_learn_id, persona_intake_id) VALUES
  ('calavera', 1, '["will","trust","intake","final"]', 'piper:es_MX-ald-medium', 'kokoro:am_adam', NULL, NULL),
  ('pinata', 1, '["games"]', NULL, NULL, NULL, NULL),
  ('oso', 1, '["ahcd","sensitive"]', NULL, NULL, NULL, NULL);
