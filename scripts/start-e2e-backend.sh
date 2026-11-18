#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export CARBON_DB_PATH="${CARBON_DB_PATH:-/tmp/cl-t2-11-e2e.db}"
export PYTHONPATH="$ROOT/backend"
rm -f "$CARBON_DB_PATH"
python -c "import migrate; migrate.run()"
exec python -m uvicorn app:app --port "${PORT:-8011}"
