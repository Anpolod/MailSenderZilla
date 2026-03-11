# MailSenderZilla: Install and Run Guide

This guide explains how to install and run MailSenderZilla locally.

## Prerequisites

- Python `3.8+`
- Node.js `16+` and `npm`
- Git

Check versions:

```bash
python3 --version
node --version
npm --version
```

## 1. Clone the project

```bash
git clone <your-repo-url> MailSenderZilla
cd MailSenderZilla
```

## 2. Install dependencies

## Option A (recommended): automatic setup

```bash
chmod +x setup.sh
./setup.sh
```

What this does:
- creates `.venv` if missing,
- installs Python dependencies from `requirements.txt`,
- runs DB migration (`python -m backend.migrate`),
- installs frontend dependencies in `frontend/`.

## Option B: manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m backend.migrate
cd frontend
npm install
cd ..
```

## 3. Run the app (development mode)

Run backend in terminal #1:

```bash
source .venv/bin/activate
python -m backend.app
```

Backend URL: `http://localhost:5000`

Run frontend in terminal #2:

```bash
cd frontend
npm run dev
```

Frontend URL: `http://localhost:3000`

You can also use helper scripts:

```bash
./run_backend.sh
./run_frontend.sh
```

## 4. Run the app (production-like local mode)

Build frontend once:

```bash
cd frontend
npm run build
cd ..
```

Start backend:

```bash
source .venv/bin/activate
python -m backend.app
```

Open: `http://localhost:5000`

## 5. Optional environment variables

You can create a `.env` file in project root:

```env
SECRET_KEY=change-me
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## 6. First run checks

- Ensure `Main_DataBase.db` exists after migration.
- Open `http://localhost:3000` in dev mode.
- Create a test campaign with a small CSV file.

## 7. Troubleshooting

- Port `5000` busy: stop conflicting process or run backend on another port.
- Port `3000` busy: run `npm run dev -- --port 3001`.
- `ModuleNotFoundError`: activate `.venv` and reinstall `pip install -r requirements.txt`.
- Frontend cannot reach API: verify backend is running on `http://localhost:5000`.

## 8. Ubuntu Server deployment (systemd + nginx)

Preconditions:
- project path: `/home/deploy/mailsenderzilla`
- frontend already built (`frontend/dist`)
- backend dependencies installed in `.venv`

### 8.1 Install and enable backend service

```bash
sudo cp deploy/systemd/mailsenderzilla.service /etc/systemd/system/mailsenderzilla.service
sudo systemctl daemon-reload
sudo systemctl enable mailsenderzilla
sudo systemctl restart mailsenderzilla
sudo systemctl status mailsenderzilla --no-pager -l
```

### 8.2 Configure nginx reverse proxy

```bash
sudo cp deploy/nginx/mailsenderzilla.conf /etc/nginx/sites-available/mailsenderzilla.conf
sudo ln -sf /etc/nginx/sites-available/mailsenderzilla.conf /etc/nginx/sites-enabled/mailsenderzilla.conf
sudo nginx -t
sudo systemctl reload nginx
```

If you have duplicate `server_name` entries, disable old site configs that use the same IP/domain to avoid nginx warnings and unexpected routing.

### 8.3 Verify API and frontend route wiring

```bash
curl -i --max-time 5 http://127.0.0.1:5000/api/settings
curl -i --max-time 5 http://127.0.0.1/api/settings
curl -i --max-time 5 http://127.0.0.1/api/campaigns
```

Expected result: backend endpoints return `200`/`[]` (not `404`/`502`).
