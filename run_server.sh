#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ -f ".env.production" ]; then
  set -a
  # shellcheck source=/dev/null
  source ".env.production"
  set +a
fi

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Create it first: python3 -m venv .venv"
  exit 1
fi

# shellcheck source=/dev/null
source ".venv/bin/activate"

echo "Installing backend dependencies..."
python -m pip install -r requirements.txt

echo "Running backend migration..."
python -m backend.migrate

echo "Installing frontend dependencies and building production bundle..."
cd frontend
npm ci || npm install
npm run build
cd "$ROOT_DIR"

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^mailsenderzilla\.service'; then
  echo "Restarting mailsenderzilla service..."
  sudo systemctl daemon-reload
  sudo systemctl restart mailsenderzilla
  sudo systemctl status mailsenderzilla --no-pager -l
else
  echo "systemd service not found. Starting gunicorn in foreground..."
  exec .venv/bin/gunicorn --chdir "$ROOT_DIR" -w 2 --threads 8 -b "${HOST:-127.0.0.1}:${PORT:-5000}" backend.wsgi:application
fi

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^nginx\.service'; then
  echo "Reloading nginx..."
  sudo nginx -t
  sudo systemctl reload nginx
fi
