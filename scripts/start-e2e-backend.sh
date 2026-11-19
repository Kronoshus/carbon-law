#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export CARBON_DB_PATH="${CARBON_DB_PATH:-/tmp/cl-e2e-${PORT:-8011}.db}"   # one database per port: parallel runs never share one
export PYTHONPATH="$ROOT/backend"
rm -f "$CARBON_DB_PATH"
${PYTHON:-python} -c "import migrate; migrate.run()"
${PYTHON:-python} "$ROOT/scripts/seed-e2e-content.py"
exec ${PYTHON:-python} -m uvicorn app:app --port "${PORT:-8011}"
