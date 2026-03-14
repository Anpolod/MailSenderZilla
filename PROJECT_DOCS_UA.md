# MailSenderZilla: Повна Документація (UA)

## 1. Призначення

`MailSenderZilla` — веб-система для запуску та керування email-кампаніями:
- створення кампаній з CSV або з таблиць БД,
- відправка через MailerSend або Gmail,
- моніторинг прогресу та лог-файлів кампаній,
- збереження шаблонів листів,
- blacklist і backup/restore БД.

## 2. Технічний стек

- Backend: Flask + SQLAlchemy
- Frontend: React + Vite
- БД: SQLite (`Main_DataBase.db`)
- Production: Gunicorn + systemd + Nginx

## 3. Структура проекту

```text
MailSenderZilla/
├── backend/
│   ├── app.py                 # Flask API + роутинг
│   ├── wsgi.py                # WSGI entrypoint для gunicorn
│   ├── services/
│   │   ├── campaign_service.py
│   │   └── template_engine.py
│   ├── models/
│   │   └── database.py
│   └── migrate*.py            # міграції/оновлення схеми
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

## 4. Режими роботи

### 4.1 Development
- Backend: `python -m backend.app`
- Frontend: `npm run dev`
- ENV: `.env.development`
- Зручний запуск: `./run_local.sh`

### 4.2 Production
- Backend: `gunicorn backend.wsgi:application`
- Process manager: `systemd` (`mailsenderzilla.service`)
- Reverse proxy + static: `nginx`
- Frontend: `frontend/dist`
- ENV: `.env.production`
- Оновлення/деплой: `./run_server.sh`
- GitHub Actions deploy helper: `deploy/remote_update.sh`

## 5. ENV-конфігурація

Головні змінні:
- `APP_ENV` = `development` або `production`
- `HOST`, `PORT`
- `SECRET_KEY`
- `MAILSENDER_DEBUG`
- `FRONTEND_HOST`, `FRONTEND_PORT`
- `VITE_API_URL`, `VITE_SOCKET_URL`, `VITE_BACKEND_URL`

Файли:
- `/.env.example`
- `/.env.development`
- `/.env.production`

## 6. Локальний запуск

```bash
cd /Users/andriipolodiienko/Documents/dev/projects/MailSenderZilla
cp .env.example .env.development
./setup.sh
./run_local.sh
```

Після старту:
- frontend: `http://localhost:3000`
- backend API: `http://localhost:5001` (або ваш `PORT` у `.env.development`)

## 7. Продакшн деплой (Ubuntu)

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

Перевірка:
```bash
curl -i --max-time 10 http://127.0.0.1:5000/api/settings
curl -i --max-time 10 http://127.0.0.1/api/campaigns
```

## 8. Оновлення сервера з git

```bash
cd /home/deploy/mailsenderzilla
git pull origin main
./run_server.sh
sudo systemctl restart mailsenderzilla
sudo nginx -t && sudo systemctl reload nginx
```

## 9. API (основні ендпоінти)

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
- `GET /api/campaigns/{id}/log-file`
- `GET /api/campaigns/{id}/log-download`
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

## 10. Логування

- Логи кампаній пишуться у `logs/campaigns/campaign_<id>.log`
- Браузер більше не стрімить логи автоматично на сторінку
- Лог можна відкрити або завантажити за запитом зі сторінки кампанії

## 11. База даних

SQLite: `Main_DataBase.db`

Основні таблиці:
- `settings`
- `campaigns`
- `campaign_deliveries`
- `logs`
- `blacklist`
- `templates`

`campaign_deliveries` зберігає по одному запису на email у межах кампанії зі статусом:
- `pending`
- `sent`
- `failed`

Важлива поведінка:
- `resume` пропускає email, які вже позначені як `sent`
- `restart` очищає delivery-state і запускає кампанію з нуля
- кампанії, створені до цього патчу, не мають автоматичного backfill історії по кожному recipient

Важливо:
- `.db` не зберігається в git (`.gitignore`)
- `git pull` не переносить дані БД між машинами

## 12. CI/CD

- GitHub Actions workflow: `.github/workflows/ci-cd.yml`
- Автоматичний CI на `pull_request` і `push` у `main/master`
- Ручний production deploy через `workflow_dispatch`
- Скрипт серверного деплою: `deploy/remote_update.sh`
- Інструкція: `deploy/GITHUB_ACTIONS_CICD.md`

## 13. Шаблони листів

- Базовий шаблон: `templates/template.html`
- Рендер і нормалізація: `backend/services/template_engine.py`
- Прев’ю: `POST /api/preview/email`

## 14. Поточні UX-особливості

- Форма кампанії: двоколонковий лаконічний layout
- `Sender Email`: вибір із:
  - `asap@asap-crew.com`
  - `info@asap-crew.com`
- Вибір таблиць БД: чекбокси + права панель конфігурації
- Dashboard: кругові індикатори на картці кампанії:
  - Sent total
  - Sent today
  - Left

## 15. Swagger / OpenAPI для тестування

Доступно:
- `GET /api/openapi.json` — OpenAPI-специфікація
- `GET /api/docs` — Swagger UI

Використання:
1. Відкрити `http://<host>/api/docs`
2. Виконувати запити прямо з UI
3. Перевіряти відповіді й коди статусів

## 16. Troubleshooting

Сервіс:
```bash
sudo systemctl status mailsenderzilla --no-pager -l
sudo journalctl -u mailsenderzilla -n 200 --no-pager
```

Порт:
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
