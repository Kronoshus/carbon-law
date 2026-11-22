#!/bin/bash
# Build and start the backend exactly as Render does (repo root, root requirements.txt, uvicorn backend.app:app), then hit /health.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$(mktemp -d)/venv"
PY="${PYTHON_VERSION:-3.11}"
if command -v uv >/dev/null; then uv venv -q -p "$PY" "$VENV"; uv pip install -q -p "$VENV/bin/python" -r requirements.txt
else python3 -m venv "$VENV"; "$VENV/bin/pip" install -q -r requirements.txt; fi
PORT="${PORT:-8099}"
export CARBON_DB_PATH="$(mktemp -d)/render-check.db" DATABASE_URL="${DATABASE_URL:-}"
"$VENV/bin/uvicorn" backend.app:app --host 127.0.0.1 --port "$PORT" > "$VENV/../server.log" 2>&1 &
PID=$!
for i in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:$PORT/health" >/dev/null; then echo "render check: /health ok"; kill $PID; exit 0; fi
  if ! kill -0 $PID 2>/dev/null; then break; fi
  sleep 1
done
echo "render check: the server did not start"; cat "$VENV/../server.log"; kill $PID 2>/dev/null; exit 1
