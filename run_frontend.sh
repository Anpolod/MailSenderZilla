#!/bin/bash
# Frontend startup script for MailSenderZilla

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT_DIR/.env.development" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ROOT_DIR/.env.development"
    set +a
fi

cd "$ROOT_DIR/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🚀 Starting frontend dev server..."
echo "Frontend will be available at http://${FRONTEND_HOST:-localhost}:${FRONTEND_PORT:-3000}"
echo "Make sure the backend is running on http://${HOST:-localhost}:${PORT:-5000}"
echo ""
npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}"
