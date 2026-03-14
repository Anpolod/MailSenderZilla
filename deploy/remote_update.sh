#!/usr/bin/env bash
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/home/deploy/mailsenderzilla}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

cd "$DEPLOY_PATH"

echo "==> Deploy path: $DEPLOY_PATH"
echo "==> Branch: $DEPLOY_BRANCH"

if [ ! -d ".git" ]; then
  echo "Repository not found in $DEPLOY_PATH"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Missing virtual environment in $DEPLOY_PATH/.venv"
  exit 1
fi

if [ ! -f "frontend/package-lock.json" ]; then
  echo "Missing frontend/package-lock.json"
  exit 1
fi

echo "==> Fetch latest code"
git fetch --all --prune
git checkout "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"

echo "==> Activate virtualenv"
# shellcheck source=/dev/null
source ".venv/bin/activate"

echo "==> Install backend dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "==> Run backend migration"
python -m backend.migrate

echo "==> Build frontend"
cd frontend
npm ci
npm run build
cd "$DEPLOY_PATH"

echo "==> Restart systemd service"
if ! sudo -n systemctl daemon-reload; then
  echo "sudo without password is required for systemctl daemon-reload"
  exit 1
fi

sudo -n systemctl restart mailsenderzilla
sudo -n systemctl status mailsenderzilla --no-pager -l

if command -v nginx >/dev/null 2>&1; then
  echo "==> Validate and reload nginx"
  sudo -n nginx -t
  sudo -n systemctl reload nginx
fi

echo "==> Health check"
curl -fsS --max-time 10 http://127.0.0.1:5000/api/settings >/dev/null

echo "Deployment completed successfully."
