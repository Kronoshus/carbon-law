#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export CARBON_DB_PATH="${CARBON_DB_PATH:-/tmp/cl-e2e-${PORT:-8011}.db}"   # one database per port: parallel runs never share one
export PYTHONPATH="$ROOT/backend"
# Tests never call a paid model: the model address is a closed local port and no real key is passed on
# (backend/app.py's demo path loads ~/.config/carbon-law/beam.env, which does not override variables already set).
export BEAM_BASE_URL="http://127.0.0.1:9" BEAM_API_KEY="e2e-no-model"
unset REFLECTION_API_KEY ANTHROPIC_API_KEY
rm -f "$CARBON_DB_PATH"
${PYTHON:-python} -c "import migrate; migrate.run()"
${PYTHON:-python} "$ROOT/scripts/seed-e2e-content.py"
exec ${PYTHON:-python} -m uvicorn app:app --port "${PORT:-8011}"
