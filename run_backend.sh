#!/bin/bash
# Backend startup script for MailSenderZilla

set -e

cd "$(dirname "$0")"

# Load development environment defaults
if [ -f ".env.development" ]; then
    set -a
    # shellcheck source=/dev/null
    source ".env.development"
    set +a
fi
export APP_ENV="${APP_ENV:-development}"
PORT="${PORT:-5000}"
AUTO_KILL_BACKEND="${AUTO_KILL_BACKEND:-0}"

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
        echo "Port $PORT is already in use."
        echo "Stop existing process first (example):"
        echo "  lsof -nP -iTCP:$PORT -sTCP:LISTEN"
        echo "  pkill -f \"python -m backend.app\""
        echo "Or set AUTO_KILL_BACKEND=1 to auto-stop previous backend process."
        echo "Or set another PORT in .env.development."
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate

# Run database migration if needed
echo "🔄 Checking database..."
python3 -m backend.migrate 2>/dev/null || python -m backend.migrate 2>/dev/null || echo "Database already initialized"

# Start Flask backend
echo "🚀 Starting Flask backend..."
echo "Backend will be available at http://${HOST:-localhost}:${PORT}"
echo ""
python3 -m backend.app 2>/dev/null || python -m backend.app
