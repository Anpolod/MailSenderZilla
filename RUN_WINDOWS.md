# Running MailSenderZilla on Windows

## Prerequisites

1. **Python 3.8 or higher** - Download from [python.org](https://www.python.org/downloads/)
2. **Node.js 16+ and npm** - Download from [nodejs.org](https://nodejs.org/)
   - **Important:** After installing Node.js, **restart your terminal/PowerShell** for the PATH to update
   - Verify installation: `node --version` and `npm --version`
3. **MailerSend API token OR Gmail App Password** (for email sending)

## Initial Setup (First Time Only)

### Step 1: Create Python Virtual Environment

Open PowerShell in the project directory and run:

```powershell
python -m venv .venv
```

### Step 2: Activate Virtual Environment

```powershell
.venv\Scripts\activate
```

You should see `(.venv)` in your prompt.

### Step 3: Install Python Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Initialize Database

```powershell
python -m backend.migrate
```

This creates `Main_DataBase.db` with required tables.

### Step 5: Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

## Running the Application

### Development Mode (Recommended)

You need **two terminals** running simultaneously:

#### Terminal 1: Backend Server

```powershell
# Activate virtual environment
.venv\Scripts\activate

# Run backend
python -m backend.app
```

Backend will be available at: **http://localhost:5000**

#### Terminal 2: Frontend Dev Server

```powershell
cd frontend
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### Production Mode

1. **Build the frontend:**
   ```powershell
   cd frontend
   npm run build
   cd ..
   ```

2. **Run backend (serves built frontend):**
   ```powershell
   .venv\Scripts\activate
   python -m backend.app
   ```

   Application will be available at: **http://localhost:5000**

## Quick Start Commands

For PowerShell, you can use these one-liners:

### Backend:
```powershell
.venv\Scripts\activate; python -m backend.app
```

### Frontend:
```powershell
cd frontend; npm run dev
```

## Troubleshooting

### "python is not recognized"
- Make sure Python is installed and added to PATH
- Try `python3` instead of `python`
- Restart PowerShell after installing Python

### "npm is not recognized" or "node is not recognized"
- **If not installed:** Install Node.js from [nodejs.org](https://nodejs.org/) (download the LTS version)
- **After installation:** Close and restart PowerShell/terminal completely (PATH updates require a new session)
- **To verify:** Run `node --version` and `npm --version` after restarting
- **If still not working:** Manually add Node.js to PATH or reinstall Node.js

### Port 5000 or 3000 already in use
- Close other applications using these ports
- Or modify ports in:
  - Backend: `backend/app.py` (line 309)
  - Frontend: `frontend/vite.config.js` (line 7)

### Database errors
- Delete `Main_DataBase.db` and run `python -m backend.migrate` again

### Module import errors
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## Next Steps

1. Open **http://localhost:3000** in your browser (development mode)
2. Or open **http://localhost:5000** (production mode)
3. Upload a CSV file with email addresses
4. Configure your email provider (MailerSend or Gmail)
5. Create and start a campaign!

## Environment Variables (Optional)

Create a `.env` file in the project root:

```
SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```
