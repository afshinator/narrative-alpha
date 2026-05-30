#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Narrative Alpha Demo ==="
echo ""

# Load env vars from .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export NARRATIVE_ALPHA_ROOT="${NARRATIVE_ALPHA_ROOT:-$HOME/.narrative_alpha}"

echo "Starting backend on port 3001 ..."
uvicorn narrative.server:app --host 0.0.0.0 --port 3001 &
BACKEND_PID=$!

sleep 2

echo "Starting dashboard on port 5173 ..."
cd dashboard && npm run dev &
DASHBOARD_PID=$!

echo ""
echo "Backend:   http://localhost:3001  (PID $BACKEND_PID)"
echo "Dashboard: http://localhost:5173  (PID $DASHBOARD_PID)"
echo ""
echo "Press Ctrl+C to stop both."

cleanup() {
  echo ""
  echo "Shutting down ..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$DASHBOARD_PID" 2>/dev/null || true
  exit 0
}

trap cleanup INT TERM
wait
