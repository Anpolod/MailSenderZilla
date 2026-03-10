#!/bin/bash
# Setup script for MailSenderZilla

set -e

cd "$(dirname "$0")"

echo "🔧 Setting up MailSenderZilla..."
echo ""

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Initialize database
echo "🗄️  Initializing database..."
python3 -m backend.migrate || python -m backend.migrate

# Install Node.js dependencies (if Node.js is available)
if command -v npm &> /dev/null; then
    echo "📦 Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "⚠️  Node.js/npm not found. Skipping frontend setup."
    echo "   Install Node.js to run the frontend: brew install node"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the backend:"
echo "  ./run_backend.sh"
echo ""
echo "To run the frontend (in a separate terminal):"
echo "  ./run_frontend.sh"
echo ""
