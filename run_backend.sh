#!/bin/bash
# Backend startup script for MailSenderZilla

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Run database migration if needed
echo "🔄 Checking database..."
python3 -m backend.migrate 2>/dev/null || python -m backend.migrate 2>/dev/null || echo "Database already initialized"

# Start Flask backend
echo "🚀 Starting Flask backend..."
echo "Backend will be available at http://localhost:5000"
echo ""
python3 -m backend.app 2>/dev/null || python -m backend.app

