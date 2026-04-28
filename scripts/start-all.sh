#!/usr/bin/env bash
# Start both the Discord bot and the web API server.
# Logs are written to logs/bot.log and logs/api.log.
# Send SIGTERM/SIGINT to stop both processes.
set -euo pipefail

SKIP_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build|--no-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--skip-build|--no-build]"
      echo ""
      echo "  --skip-build, --no-build  Skip frontend build before starting services"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--skip-build|--no-build]" >&2
      exit 1
      ;;
  esac
done

cd "$(dirname "$0")/.."

mkdir -p logs

cleanup() {
  echo "Stopping processes..."
  kill "$BOT_PID" "$API_PID" 2>/dev/null || true
  wait "$BOT_PID" "$API_PID" 2>/dev/null || true
  echo "Done."
}
trap cleanup SIGINT SIGTERM EXIT

if [[ "$SKIP_BUILD" -eq 1 ]]; then
  echo "Skipping frontend build (--skip-build)."
else
  echo "Building frontend..."
  (cd frontend && npm run build)
  echo "Frontend build complete."
fi

echo "Starting Discord bot..."
uv run python -m src.main >> logs/bot.log 2>&1 &
BOT_PID=$!

echo "Starting web API server..."
uv run uvicorn "src.api.app:create_app" \
  --factory \
  --host "${WEB_HOST:-0.0.0.0}" \
  --port "${WEB_PORT:-8000}" \
  >> logs/api.log 2>&1 &
API_PID=$!

echo "Bot PID: $BOT_PID  |  API PID: $API_PID"
echo "Logs: logs/bot.log, logs/api.log"
echo "Press Ctrl+C to stop."

wait "$BOT_PID" "$API_PID"
