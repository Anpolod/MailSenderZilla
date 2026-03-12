# MailSenderZilla: Full Project Documentation (EN)

## 1. Purpose

`MailSenderZilla` is a web-based system for managing email campaigns:
- create campaigns from CSV files or database tables,
- send via MailerSend or Gmail,
- monitor progress and logs in real time,
- manage email templates,
- maintain blacklist and database backups.

## 2. Tech Stack

- Backend: Flask + Flask-SocketIO + SQLAlchemy
- Frontend: React + Vite
- Database: SQLite (`Main_DataBase.db`)
- Production runtime: Gunicorn + systemd + Nginx

## 3. Project Structure

```text
MailSenderZilla/
├── backend/
│   ├── app.py                 # Flask API + WS + routes
│   ├── wsgi.py                # WSGI entrypoint for gunicorn
│   ├── services/
│   │   ├── campaign_service.py
│   │   └── template_engine.py
│   ├── models/
│   │   └── database.py
│   └── migrate*.py            # schema updates/migrations
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── services/api.js
│   └── vite.config.js
├── templates/
│   └── template.html
├── deploy/
│   ├── systemd/mailsenderzilla.service
│   └── nginx/mailsenderzilla.conf
├── .env.example
├── .env.development
├── .env.production
├── run_local.sh
├── run_server.sh
├── DEPLOYMENT.md
└── Main_DataBase.db
```

## 4. Runtime Modes

### 4.1 Development
- Backend: `python -m backend.app`
- Frontend: `npm run dev`
- ENV file: `.env.development`
- Convenient launcher: `./run_local.sh`

### 4.2 Production
- Backend: `gunicorn backend.wsgi:application`
- Process manager: `systemd` (`mailsenderzilla.service`)
- Reverse proxy + static hosting: `nginx`
- Frontend build output: `frontend/dist`
- ENV file: `.env.production`
- Update/deploy helper: `./run_server.sh`

## 5. Environment Configuration

Key variables:
- `APP_ENV` = `development` or `production`
- `HOST`, `PORT`
- `SECRET_KEY`
- `MAILSENDER_DEBUG`
- `FRONTEND_HOST`, `FRONTEND_PORT`
- `VITE_API_URL`, `VITE_SOCKET_URL`, `VITE_BACKEND_URL`

Files:
- `/.env.example`
- `/.env.development`
- `/.env.production`

## 6. Local Development

```bash
cd /Users/andriipolodiienko/Documents/dev/projects/MailSenderZilla
cp .env.example .env.development
./setup.sh
./run_local.sh
```

After startup:
- frontend: `http://localhost:3000`
- backend API: `http://localhost:5001` (or your configured `PORT`)

## 7. Production Deployment (Ubuntu)

```bash
cd /home/deploy/mailsenderzilla
git pull origin main
./run_server.sh

sudo cp deploy/systemd/mailsenderzilla.service /etc/systemd/system/mailsenderzilla.service
sudo systemctl daemon-reload
sudo systemctl restart mailsenderzilla

sudo cp deploy/nginx/mailsenderzilla.conf /etc/nginx/sites-available/mailsenderzilla.conf
sudo ln -sf /etc/nginx/sites-available/mailsenderzilla.conf /etc/nginx/sites-enabled/mailsenderzilla.conf
sudo nginx -t
sudo systemctl reload nginx
```

Health checks:
```bash
curl -i --max-time 10 http://127.0.0.1:5000/api/settings
curl -i --max-time 10 http://127.0.0.1/api/campaigns
```

## 8. Server Updates from Git

```bash
cd /home/deploy/mailsenderzilla
git pull origin main
./run_server.sh
sudo systemctl restart mailsenderzilla
sudo nginx -t && sudo systemctl reload nginx
```

## 9. API Overview

### Settings
- `GET /api/settings`
- `PUT /api/settings`

### Campaigns
- `GET /api/campaigns`
- `POST /api/campaigns`
- `GET /api/campaigns/{id}`
- `DELETE /api/campaigns/{id}`
- `POST /api/campaigns/{id}/start`
- `POST /api/campaigns/{id}/pause`
- `POST /api/campaigns/{id}/resume`
- `POST /api/campaigns/{id}/restart`
- `POST /api/campaigns/{id}/clone`
- `GET /api/campaigns/{id}/logs`
- `GET /api/campaigns/{id}/html`

### Upload / Blacklist / DB / Preview / Backup
- `POST /api/upload`
- `GET /api/blacklist`
- `POST /api/blacklist`
- `GET /api/database/tables`
- `GET /api/database/tables/{table}/columns`
- `GET /api/database/tables/{table}/preview`
- `POST /api/preview/email`
- `POST /api/backup`
- `GET /api/backup`
- `POST /api/backup/restore`
- `DELETE /api/backup/{path}`

## 10. WebSocket

Events:
- `connect`
- `join_campaign` (room `campaign_{id}`)
- `campaign_log` (real-time log stream)

## 11. Database

SQLite file:
- `Main_DataBase.db`

Primary tables:
- `settings`
- `campaigns`
- `logs`
- `blacklist`
- `templates`

Important:
- `.db` files are ignored by git
- `git pull` does not transfer database content between machines

## 12. Email Templates

- Base template: `templates/template.html`
- Rendering/normalization: `backend/services/template_engine.py`
- Preview endpoint: `POST /api/preview/email`

## 13. Current UX Highlights

- Two-column campaign creation form
- Sender email dropdown with:
  - `asap@asap-crew.com`
  - `info@asap-crew.com`
- Database selector with checkbox list + right-side config panel
- Dashboard campaign card circular indicators:
  - Sent total
  - Sent today
  - Left

## 14. Swagger / OpenAPI

Available endpoints:
- `GET /api/openapi.json` — OpenAPI specification
- `GET /api/docs` — Swagger UI

Usage:
1. Open `http://<host>/api/docs`
2. Click `Try it out`
3. Run and inspect responses/status codes

## 15. Troubleshooting

Service:
```bash
sudo systemctl status mailsenderzilla --no-pager -l
sudo journalctl -u mailsenderzilla -n 200 --no-pager
```

Port:
```bash
ss -ltnp | grep 5000 || true
```

API:
```bash
curl -i http://127.0.0.1:5000/api/settings
curl -i http://127.0.0.1/api/campaigns
```

Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```
