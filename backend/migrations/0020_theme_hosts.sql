-- 0020: the Memento Mori theme hosts. La Calavera hosts Día de Muertos, and each other theme has its own host, who takes
-- La Calavera's part (the app casts it). No units of their own, and the voices are the defaults until the firm picks them.
INSERT INTO characters (id, enabled, units_json, voice_es, voice_en, persona_learn_id, persona_intake_id) VALUES
  ('girasol', 1, '[]', NULL, NULL, NULL, NULL),
  ('colibri', 1, '[]', NULL, NULL, NULL, NULL),
  ('velita', 1, '[]', NULL, NULL, NULL, NULL),
  ('tortuga', 1, '[]', NULL, NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;
