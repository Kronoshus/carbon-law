#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export CARBON_DB_PATH="${CARBON_DB_PATH:-/tmp/cl-e2e-${PORT:-8011}.db}"   # one database per port: parallel runs never share one
export PYTHONPATH="$ROOT/backend"
# Tests never call a paid model: the model address is a closed local port and no real key is passed on
# (backend/app.py's demo path loads ~/.config/carbon-law/beam.env, which does not override variables already set).
# The model is the local fake (scripts/e2e-fakes.py); with the fake not running, the port is closed and every call fails.
export BEAM_BASE_URL="http://127.0.0.1:${E2E_FAKE_PORT:-8291}/v1" BEAM_API_KEY="e2e-no-model"
# Stripe is the same local fake, in test mode, with a test-only webhook secret.
export STRIPE_MODE=test STRIPE_API_BASE="http://127.0.0.1:${E2E_FAKE_PORT:-8291}" STRIPE_SECRET_KEY="sk_test_e2e" STRIPE_WEBHOOK_SECRET="whsec_e2e"
export APP_ORIGIN="${APP_ORIGIN:-http://127.0.0.1:${E2E_WEB_PORT:-5173}}"
# The movable clock (T8-06) and the in-process worker (drafting, the hourly timeline tick), for this test backend only.
export APRENDE_E2E_CLOCK=1 APRENDE_INPROCESS_WORKER=1
unset REFLECTION_API_KEY ANTHROPIC_API_KEY
rm -f "$CARBON_DB_PATH"
${PYTHON:-python} -c "import migrate; migrate.run()"
${PYTHON:-python} "$ROOT/scripts/seed-e2e-content.py"
exec ${PYTHON:-python} -m uvicorn app:app --port "${PORT:-8011}"
