-- 0019: decision #54, the firm clears the conflict check with an AI-assisted review within 24 hours, any day
UPDATE settings SET value_json = '{"conflict_hours":24,"scope_bd":2,"review_bd":3,"revise_bd":2}', updated_by = 'migration', updated_at = CURRENT_TIMESTAMP
WHERE key = 'turnaround' AND value_json = '{"conflict_bd":2,"scope_bd":2,"review_bd":3,"revise_bd":2}'
