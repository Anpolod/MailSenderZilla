#!/bin/bash
# Frontend startup script for MailSenderZilla

cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🚀 Starting frontend dev server..."
echo "Frontend will be available at http://localhost:3000"
echo "Make sure the backend is running on http://localhost:5000"
echo ""
npm run dev
