# Frontend Setup Guide

## Prerequisites

Node.js and npm need to be installed to run the frontend.

### Install Node.js (macOS)

**Option 1: Using Homebrew (Recommended)**
```bash
brew install node
```

**Option 2: Download from nodejs.org**
1. Visit https://nodejs.org/
2. Download the LTS version for macOS
3. Run the installer

**Option 3: Using nvm (Node Version Manager)**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Restart terminal or source profile
source ~/.zshrc  # or ~/.bash_profile

# Install Node.js LTS
nvm install --lts
nvm use --lts
```

### Verify Installation

```bash
node --version  # Should show v18.x.x or higher
npm --version   # Should show 9.x.x or higher
```

## Running the Frontend

### Method 1: Using the Script

```bash
./run_frontend.sh
```

### Method 2: Manual Steps

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies (first time only):**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

## Development Mode

When running `npm run dev`:
- Frontend runs on port 3000
- API calls are proxied to `http://localhost:5000` (backend)
- WebSocket connections are proxied to backend
- Hot module reloading is enabled

## Production Build

To build for production:

```bash
cd frontend
npm run build
```

Built files will be in `frontend/dist/` and can be served by the Flask backend.

## Troubleshooting

### "command not found: npm"

Node.js is not installed. Follow the installation steps above.

### "EACCES: permission denied"

Fix npm permissions:
```bash
sudo chown -R $(whoami) ~/.npm
```

### Port 3000 already in use

Change the port in `frontend/vite.config.js`:
```javascript
server: {
  port: 3001,  // Change this
  // ...
}
```

### Backend connection errors

Make sure the backend is running:
```bash
python -m backend.app
```

The backend should be accessible at `http://localhost:5000`.

