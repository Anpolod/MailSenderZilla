# MailSenderZilla – Global Cursor Rules  (single document)

--------------------------------------------------------------------------------
1  Project tree (current structure)
--------------------------------------------------------------------------------
MailSenderZilla/  
├── backend/                      # Flask backend application
│   ├── __init__.py
│   ├── app.py                    # Flask application entry point
│   ├── migrate.py                # Database migration (initial)
│   ├── migrate_add_*.py          # Additional migrations
│   ├── mailer/                   # Email sending strategies
│   │   ├── __init__.py
│   │   ├── base.py               # BaseMailer abstract class
│   │   ├── mailersend.py         # MailerSend API implementation
│   │   └── gmail.py              # Gmail SMTP implementation
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── database.py           # Settings, Campaign, Log, Blacklist, Template
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── campaign_service.py   # Campaign management logic
│   │   └── template_engine.py    # Jinja2 template rendering
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── database.py           # Database operations (tables, columns, preview)
│       ├── telegram.py           # Telegram notifications
│       ├── export.py             # CSV export utilities
│       └── backup.py             # Database backup utilities
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── App.jsx               # Main React component with routing
│   │   ├── main.jsx              # React entry point
│   │   ├── App.css               # Global styles
│   │   ├── components/           # React components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CampaignCard.jsx
│   │   │   ├── CampaignForm.jsx
│   │   │   ├── CampaignDetail.jsx
│   │   │   ├── CSVUploader.jsx
│   │   │   ├── DatabaseSelector.jsx
│   │   │   ├── LogPanel.jsx
│   │   │   ├── EmailPreviewModal.jsx
│   │   │   ├── SettingsModal.jsx
│   │   │   ├── TemplateManager.jsx
│   │   │   └── TemplateSelector.jsx
│   │   └── services/
│   │       └── api.js            # Frontend API client
│   ├── package.json              # Node.js dependencies
│   ├── vite.config.js            # Vite configuration with proxy
│   └── dist/                     # Built frontend (production)
├── templates/
│   └── template.html             # Master HTML email template (Jinja2)
├── uploads/                      # Uploaded CSV files (gitignored)
├── backups/                      # Database backups (gitignored)
├── examples/                     # Sample files
│   ├── main.py                   # CLI prototype (reference)
│   └── officers.txt              # Vacancy text sample
├── Main_DataBase.db              # SQLite database (gitignored, auto-generated)
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── README.md                     # Main documentation
├── README_RU.md                  # Russian documentation
├── RUN_WINDOWS.md                # Windows-specific instructions
└── IMPROVEMENTS.md               # Feature improvement roadmap

--------------------------------------------------------------------------------
2  Python & dependencies
--------------------------------------------------------------------------------
* Target: **Python 3.8+** (tested on 3.12)
* Backend uses Flask, Flask-SocketIO, SQLAlchemy, pandas, Jinja2
* Dependencies listed in `requirements.txt`
* Do **not** install packages implicitly inside code
* Use virtual environment (`.venv/`) - never commit it to Git

Key dependencies:
- Flask==2.3.3
- Flask-SocketIO==5.3.6
- SQLAlchemy>=2.0.45
- pandas==2.2.3
- Jinja2==3.1.2
- python-dotenv>=1.0.0

Frontend:
- React 18
- Vite
- React Router
- Socket.IO Client
- Axios

--------------------------------------------------------------------------------
3  Secrets & environment variables
--------------------------------------------------------------------------------
Load exclusively from `.env` using `python-dotenv`.  
Expected keys (add more via ENV, never hard-code):

Backend:
- SECRET_KEY                        # Flask secret key
- MAILERSEND_TOKEN                  # MailerSend API token (or use Settings in DB)
- GMAIL_USER                        # Gmail username (optional)
- GMAIL_APP_PASSWORD                # Gmail app password (or use Settings in DB)
- TELEGRAM_BOT_TOKEN                # Telegram bot token (or use Settings in DB)
- TELEGRAM_CHAT_ID                  # Telegram chat ID (or use Settings in DB)

Cursor must never print real values in logs or error messages.

Credentials can also be stored in database `settings` table:
- `mailersend_api_token`
- `gmail_app_password`
- `telegram_bot_token`
- `telegram_chat_id`

--------------------------------------------------------------------------------
4  Runtime isolation
--------------------------------------------------------------------------------
**Development:**
- Backend: `python -m backend.app` (runs on port 5000)
- Frontend: `cd frontend && npm run dev` (runs on port 3000, proxies to backend)

**Production:**
- Build frontend: `cd frontend && npm run build`
- Backend serves static files from `frontend/dist/`
- Run: `python -m backend.app`

**Docker (recommended for production):**

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/Main_DataBase.db:/app/Main_DataBase.db \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/backups:/app/backups \
  -p 5000:5000 \
  mailsenderzilla
```

Container may egress only:
- `api.mailersend.com`
- `smtp.gmail.com`
- `api.telegram.org`

---

## 5  Email campaign workflow (web-based)

1. **Create Campaign** (via web UI):
   - User provides campaign name, subject, sender email
   - Choose provider (MailerSend or Gmail)
   - Select data source: CSV upload OR database table
   - Configure batch size, delays, daily limits
   - Add email content (HTML body or plain text vacancies)
   - Save template (optional)

2. **Email source**:
   - CSV file: uploaded to `uploads/`, auto-detect email column
   - Database table: read from `Main_DataBase.db`, select table and email column

3. **Validation**:
   - `validate_email()` regex check
   - Length ≤ 320 characters
   - Deduplication
   - Blacklist filtering (from `blacklist` table)

4. **Template rendering**:
   - Use `TemplateEngine` (Jinja2)
   - Render `templates/template.html` with variables:
     - `{{ vacancies }}` - formatted vacancy text
     - `{{ cta_subject }}` - call-to-action subject
     - `{{ cta_body }}` - call-to-action body
   - Or use custom HTML body directly

5. **Send**:
   - Use `CampaignService.run_campaign()`
   - MailerSend: REST API via `MailerSendMailer`
   - Gmail: SMTP via `GmailMailer`
   - Batch processing with configurable delays
   - Rate limiting (MailerSend: 429/409 handling, Gmail: 2000/day limit)

6. **Status tracking**:
   - Campaign status: `pending`, `running`, `paused`, `completed`, `failed`
   - Update `success_cnt` and `error_cnt` in `campaigns` table
   - Log all actions to `logs` table
   - Real-time WebSocket updates to frontend

7. **Campaign management**:
   - Start, pause, resume, restart campaigns
   - Export results: logs, sent emails, failed emails, statistics
   - Clone campaigns for quick reuse

---

## 6  Parallel campaigns

`ThreadPoolExecutor(max_workers=5)` in `backend/app.py` - allows up to 5 campaigns running simultaneously.

Each campaign runs in its own thread:
- Independent batch processing
- Separate error handling
- Individual WebSocket log streams
- Status updates in database

---

## 7  HTML templating

Base file: `templates/template.html` uses Jinja2 placeholders:

- `{{ vacancies }}` - Formatted vacancy text (HTML)
- `{{ cta_subject }}` - Call-to-action subject/heading  
- `{{ cta_body }}` - Call-to-action body text (HTML)

Template engine (`backend/services/template_engine.py`):
- Plain text → HTML conversion (preserves line breaks)
- Variable substitution
- Default template fallback

Templates can be saved in database (`templates` table) for reuse.

---

## 8  Logging & alerts

* Default level: INFO
* Logs stored in database (`logs` table):
  - `campaign_id` - Foreign key to campaign
  - `level` - INFO, WARNING, ERROR, SUCCESS
  - `message` - Log message
  - `ts` - Timestamp

* Real-time streaming:
  - Flask-SocketIO WebSocket events
  - Frontend receives `campaign_log` events
  - LogPanel component displays logs in real-time

* Telegram integration:
  - Campaign start notifications
  - Batch completion updates
  - Error alerts
  - Campaign completion summary
  - Uses `backend/utils/telegram.py`

* On send failure:
  - Write error to database log
  - Send Telegram alert (if configured)
  - Update campaign `error_cnt`
  - Continue with next batch

---

## 9  Database models

**Settings** (`settings` table):
- Key-value store for application settings
- Keys: `mailersend_api_token`, `gmail_app_password`, `telegram_bot_token`, `telegram_chat_id`

**Campaign** (`campaigns` table):
- Campaign metadata and configuration
- Status tracking (pending, running, paused, completed, failed)
- Success/error counts
- Stored email content (`html_body`, `vacancies_text`)

**Log** (`logs` table):
- Campaign execution logs
- Linked to campaigns via `campaign_id`
- Levels: INFO, WARNING, ERROR, SUCCESS

**Blacklist** (`blacklist` table):
- Email addresses to exclude from campaigns
- Reasons: 'unsubscribe', 'bounce', 'manual', etc.

**Template** (`templates` table):
- Saved email templates
- Name, subject, html_body, vacancies_text

**Migration:**
- Run migrations automatically on app startup
- Additional migrations: `migrate_add_database_table.py`, `migrate_add_email_content.py`, `migrate_add_templates.py`

---

## 10  API endpoints (REST)

**Campaigns:**
- `GET /api/campaigns` - List all campaigns
- `GET /api/campaigns/<id>` - Get campaign details
- `POST /api/campaigns` - Create and start campaign
- `POST /api/campaigns/<id>/start` - Start pending campaign
- `POST /api/campaigns/<id>/pause` - Pause running campaign
- `POST /api/campaigns/<id>/resume` - Resume paused campaign
- `POST /api/campaigns/<id>/restart` - Restart completed/failed campaign
- `POST /api/campaigns/<id>/clone` - Clone campaign
- `DELETE /api/campaigns/<id>` - Delete campaign
- `GET /api/campaigns/<id>/logs` - Get campaign logs
- `GET /api/campaigns/<id>/export/logs` - Export logs CSV
- `GET /api/campaigns/<id>/export/sent` - Export sent emails CSV
- `GET /api/campaigns/<id>/export/failed` - Export failed emails CSV
- `GET /api/campaigns/<id>/export/all` - Export all emails CSV
- `GET /api/campaigns/<id>/export/statistics` - Export statistics CSV

**Settings:**
- `GET /api/settings` - Get all settings
- `PUT /api/settings` - Update settings

**Templates:**
- `GET /api/templates` - List all templates
- `GET /api/templates/<id>` - Get template
- `POST /api/templates` - Create template
- `PUT /api/templates/<id>` - Update template
- `DELETE /api/templates/<id>` - Delete template

**Database:**
- `GET /api/database/tables` - List all tables
- `GET /api/database/tables/<table>/columns` - Get table columns
- `GET /api/database/tables/<table>/preview` - Preview table data

**Upload:**
- `POST /api/upload` - Upload CSV file

**Preview:**
- `POST /api/preview/email` - Preview rendered email HTML

**Backup:**
- `GET /api/backup` - List backups
- `POST /api/backup` - Create backup
- `POST /api/backup/restore` - Restore from backup
- `DELETE /api/backup/<path>` - Delete backup

**Blacklist:**
- `GET /api/blacklist` - Get blacklist
- `POST /api/blacklist` - Add to blacklist

---

## 11  WebSocket events (Flask-SocketIO)

**Client → Server:**
- `connect` - Connect to server
- `join_campaign` - Join campaign log room (`{campaign_id: <id>}`)

**Server → Client:**
- `connected` - Connection confirmed
- `joined` - Room join confirmed
- `campaign_log` - New log message (`{campaign_id, level, message, timestamp}`)

---

## 12  Frontend architecture

**React Router:**
- `/` - Dashboard (list campaigns)
- `/campaign/new` - Create new campaign
- `/campaign/:id` - Campaign details

**Key Components:**
- `Dashboard` - Campaign list with filters
- `CampaignForm` - Create/edit campaign form
- `CampaignDetail` - Campaign details with logs
- `LogPanel` - Real-time log viewer with filtering
- `SettingsModal` - Application settings and backups
- `TemplateManager` - Template management

**State Management:**
- React hooks (useState, useEffect)
- API calls via `services/api.js`
- WebSocket connection for real-time logs

---

## 13  Safety rules

* No arbitrary shell commands unless user explicitly requests
* Never delete or touch user system files outside project directory
* All file operations limited to:
  - `uploads/` - CSV uploads
  - `backups/` - Database backups
  - `Main_DataBase.db` - Application database
* Validate all user inputs
* Use parameterized queries (SQLAlchemy ORM prevents SQL injection)
* Sanitize file uploads (check extensions, size limits)
* Never commit secrets to Git
* Always use `.env` or database settings for credentials

---

## 14  Code style & conventions

**Backend (Python):**
- Follow PEP 8
- Use type hints where possible
- SQLAlchemy ORM for database operations
- Logging via Python `logging` module
- Error handling with try/except and proper logging

**Frontend (JavaScript/React):**
- ES6+ syntax
- Functional components with hooks
- CSS modules or inline styles via `App.css`
- API calls centralized in `services/api.js`
- Error handling with try/catch and user-friendly messages

**Database:**
- Use migrations for schema changes
- Always add new columns via migration scripts
- Test migrations on empty database first

---

## 15  Development workflow

1. **Backend changes:**
   - Modify code in `backend/`
   - Run: `python -m backend.app`
   - Backend auto-reloads on file changes (debug mode)

2. **Frontend changes:**
   - Modify code in `frontend/src/`
   - Vite hot-reloads automatically
   - Changes visible immediately in browser

3. **Database changes:**
   - Create migration script: `backend/migrate_add_<feature>.py`
   - Add migration call in `backend/app.py` startup
   - Test migration on development database

4. **Testing:**
   - Backend: Create test campaigns, check logs
   - Frontend: Test UI interactions, WebSocket connections
   - Integration: Test full campaign flow

---

## 16  Key features implemented

✅ Multi-campaign support
✅ CSV and database table email sources
✅ MailerSend and Gmail providers
✅ Real-time logging via WebSocket
✅ Campaign pause/resume/restart
✅ Template system
✅ Export functionality (CSV)
✅ Database backup/restore
✅ Campaign cloning
✅ Advanced filtering and search
✅ Modern UI with glassmorphism effects
✅ Settings management
✅ Telegram notifications

---

# END OF GLOBAL INSTRUCTIONS
