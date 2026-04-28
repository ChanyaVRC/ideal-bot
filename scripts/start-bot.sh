#!/usr/bin/env bash
# Start the Discord bot.
# Usage: ./scripts/start-bot.sh [--reload]
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python -m src.main "$@" &
PID=$!
trap "kill $PID 2>/dev/null" INT TERM
wait $PID
