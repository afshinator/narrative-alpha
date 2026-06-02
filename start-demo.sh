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

export BACKEND_PORT="${BACKEND_PORT:-8000}"
export VITE_BACKEND_PORT="${VITE_BACKEND_PORT:-$BACKEND_PORT}"
# PORT controls the Vite listen port — set it to a port reachable by your client.
# Unset = Vite default (5173).

# ── Setup checks ────────────────────────────────────────────────────────────
# Verify the Python venv exists and can import the app's dependencies.
# Rebuilds automatically when missing or broken (e.g. after moving the repo).
if ! .venv/bin/python -c "import uvicorn, fastapi, trafilatura" 2>/dev/null; then
	echo "Python venv missing or broken — setting up..."
	if command -v uv &>/dev/null; then
		uv venv --python 3.11 --clear
		uv pip install -r requirements.txt
	else
		python3 -m venv .venv --clear
		.venv/bin/pip install -r requirements.txt
	fi
	echo ""
fi

if [ ! -d "dashboard/node_modules" ]; then
	echo "Installing dashboard dependencies..."
	cd dashboard && npm install && cd ..
	echo ""
fi
# ────────────────────────────────────────────────────────────────────────────

echo "Starting backend on port $BACKEND_PORT ..."
.venv/bin/uvicorn narrative.server:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

sleep 2

echo "Starting dashboard ..."
cd dashboard && env PORT="${PORT:-}" VITE_BACKEND_PORT="$VITE_BACKEND_PORT" npm run dev &
DASHBOARD_PID=$!

echo ""
echo "Backend:   http://localhost:$BACKEND_PORT  (PID $BACKEND_PID)"
if [ -n "${PORT:-}" ]; then
	echo "Dashboard: http://localhost:$PORT  (PID $DASHBOARD_PID)"
else
	echo "Dashboard: starting (check output above for port — Vite defaults to 5173)"
fi
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
