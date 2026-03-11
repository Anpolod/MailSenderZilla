#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ -f ".env.development" ]; then
  set -a
  # shellcheck source=/dev/null
  source ".env.development"
  set +a
fi

PORT="${PORT:-5000}"
AUTO_KILL_BACKEND="${AUTO_KILL_BACKEND:-0}"

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Run ./setup.sh first."
  exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "Missing frontend/node_modules. Run ./setup.sh first."
  exit 1
fi

# shellcheck source=/dev/null
source ".venv/bin/activate"

echo "Running DB migration..."
python -m backend.migrate

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if [ "$AUTO_KILL_BACKEND" = "1" ]; then
    echo "Port $PORT is busy. AUTO_KILL_BACKEND=1 enabled, attempting to stop old backend..."
    PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN | sort -u)"
    for pid in $PIDS; do
      cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
      if echo "$cmd" | grep -Eq 'python .*backend\.app|gunicorn .*backend\.'; then
        kill "$pid" >/dev/null 2>&1 || true
      else
        echo "Port $PORT is used by non-backend process (pid=$pid): $cmd"
        echo "Refusing to kill it automatically. Disable it manually or change PORT."
        exit 1
      fi
    done
    sleep 1
  else
    echo "Port $PORT is already in use. run_local.sh will not start a second backend."
    echo "Stop existing backend first:"
    echo "  lsof -nP -iTCP:$PORT -sTCP:LISTEN"
    echo "  pkill -f \"python -m backend.app\""
    echo "Or set AUTO_KILL_BACKEND=1 to auto-stop previous backend process."
    echo "Or change PORT in .env.development."
    exit 1
  fi
fi

echo "Starting backend (development)..."
python -m backend.app &
BACKEND_PID=$!

cleanup() {
  echo "Stopping local services..."
  if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting frontend Vite dev server..."
cd frontend
npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}"
