# MailSenderZilla Deployment Workflow

## Architecture

- Backend: Flask + Socket.IO (`backend.app`)
- Frontend: React + Vite (`frontend/`)
- Process manager: `systemd` (`mailsenderzilla.service`)
- HTTP reverse proxy: `nginx`
- App server: `gunicorn` (`backend.wsgi:application`)
- Database: SQLite (`Main_DataBase.db`)

Runtime flow in production:

1. Nginx serves `frontend/dist` as static files.
2. Nginx proxies `/api/*` and `/socket.io/*` to `127.0.0.1:5000`.
3. Systemd runs gunicorn workers.
4. Gunicorn imports `backend.wsgi`, which loads env + bootstraps DB/migrations.

## File structure (deployment-relevant)

```text
MailSenderZilla/
├── backend/
│   ├── app.py
│   └── wsgi.py
├── frontend/
│   ├── src/
│   └── dist/                    # built in production
├── deploy/
│   ├── nginx/
│   │   └── mailsenderzilla.conf
│   └── systemd/
│       └── mailsenderzilla.service
├── .env.example
├── .env.development
├── .env.production
├── run_local.sh
├── run_server.sh
└── Main_DataBase.db
```

## Local development

```bash
cp .env.example .env.development
./setup.sh
./run_local.sh
```

- Backend: `python -m backend.app` (debug mode from `.env.development`)
- Frontend: `npm run dev` with Vite proxy to backend

## Production deployment (Ubuntu)

### 1. Bootstrap server

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx nodejs npm
```

### 2. Deploy project

```bash
git clone <your-repo-url> /home/deploy/mailsenderzilla
cd /home/deploy/mailsenderzilla
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env.production
```

Edit `.env.production` and set at least `SECRET_KEY`.

### 3. Build frontend + migrate DB

```bash
./run_server.sh
```

### 4. Install systemd service

```bash
sudo cp deploy/systemd/mailsenderzilla.service /etc/systemd/system/mailsenderzilla.service
sudo systemctl daemon-reload
sudo systemctl enable mailsenderzilla
sudo systemctl restart mailsenderzilla
sudo systemctl status mailsenderzilla --no-pager -l
```

### 5. Install nginx config

```bash
sudo cp deploy/nginx/mailsenderzilla.conf /etc/nginx/sites-available/mailsenderzilla.conf
sudo ln -sf /etc/nginx/sites-available/mailsenderzilla.conf /etc/nginx/sites-enabled/mailsenderzilla.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Health checks

```bash
curl -i --max-time 5 http://127.0.0.1:5000/api/settings
curl -i --max-time 5 http://127.0.0.1/api/campaigns
```

## Updating server from git

```bash
cd /home/deploy/mailsenderzilla
git pull
./run_server.sh
sudo cp deploy/systemd/mailsenderzilla.service /etc/systemd/system/mailsenderzilla.service
sudo systemctl daemon-reload
sudo systemctl restart mailsenderzilla
sudo nginx -t && sudo systemctl reload nginx
```

## Troubleshooting quick checks

```bash
sudo systemctl status mailsenderzilla --no-pager -l
sudo journalctl -u mailsenderzilla -n 120 --no-pager
ss -ltnp | grep 5000 || true
curl -i --max-time 5 http://127.0.0.1:5000/api/settings
```
