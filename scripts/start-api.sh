#!/usr/bin/env bash
# Start the FastAPI web admin server.
# Usage: ./scripts/start-api.sh [--reload]
set -euo pipefail

cd "$(dirname "$0")/.."

RELOAD=""
if [[ "${1:-}" == "--reload" ]]; then
  RELOAD="--reload"
fi

uv run uvicorn "src.api.app:create_app" \
  --factory \
  --host "${WEB_HOST:-0.0.0.0}" \
  --port "${WEB_PORT:-8000}" \
  $RELOAD &
PID=$!
trap "kill $PID 2>/dev/null" INT TERM
wait $PID
