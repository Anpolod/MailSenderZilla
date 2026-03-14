# MailSenderZilla

A local web application for bulk email campaigns (ASAP Marine Agency) with support for MailerSend API and Gmail SMTP.

## Features

- ✅ **Web-based GUI** for managing campaigns
- ✅ **Multi-campaign support** - run several campaigns in parallel
- ✅ **Multiple providers** - MailerSend API or Gmail SMTP/OAuth
- ✅ **CSV import** with auto-detection of email columns
- ✅ **Template engine** - paste plain-text vacancies → auto-wrap into HTML
- ✅ **Real-time logging** via WebSocket
- ✅ **Rate limiting** - handles MailerSend 429/409 and Gmail daily limits
- ✅ **Email validation** - RegExp, deduplication, blacklist checking
- ✅ **Telegram integration** - stream logs to Telegram
- ✅ **SQLite database** - unified `Main_DataBase.db` for history
- ✅ **Blacklist management** - unsubscribe/bounce handling

## Project Structure

```
MailSenderZilla/
├── backend/
│   ├── app.py                 # Flask bootstrap
│   ├── migrate.py             # Database migration
│   ├── mailer/                # Sending strategies
│   │   ├── base.py
│   │   ├── mailersend.py
│   │   └── gmail.py
│   ├── models/                # SQLAlchemy ORM
│   │   └── database.py
│   ├── services/
│   │   ├── campaign_service.py
│   │   └── template_engine.py
│   └── utils/
├── frontend/
│   └── src/                   # React 18 + Vite
├── templates/
│   └── template.html          # Master HTML letter (Jinja2)
├── examples/                  # Sample files
│   ├── main.py                # CLI prototype (reference)
│   └── officers.txt           # Vacancy text sample
├── uploads/                   # Uploaded CSV files
├── Main_DataBase.db           # Unified SQLite DB (auto-generated)
├── README.md
└── requirements.txt
```

## Installation

For a full development/production workflow with `gunicorn + systemd + nginx`, see [DEPLOYMENT.md](DEPLOYMENT.md).
For GitHub Actions CI/CD setup, see [deploy/GITHUB_ACTIONS_CICD.md](deploy/GITHUB_ACTIONS_CICD.md).
Ukrainian full project documentation: [PROJECT_DOCS_UA.md](PROJECT_DOCS_UA.md).
English full project documentation: [PROJECT_DOCS_EN.md](PROJECT_DOCS_EN.md).
API interactive docs (Swagger UI): `/api/docs` (OpenAPI JSON: `/api/openapi.json`).

### Platform-Specific Guides

- **Windows**: See [RUN_WINDOWS.md](RUN_WINDOWS.md)
- **macOS**: See [RUN_MACOS.md](RUN_MACOS.md) | [Quick Start](QUICK_START_MACOS.md) | [Transfer Guide](ПЕРЕНОС_НА_MACOS.md)

### Prerequisites

- Python 3.8 or higher
- Node.js 16+ and npm (for frontend)
- MailerSend API token OR Gmail App Password

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd MailSenderZilla
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database:**
   ```bash
   python -m backend.migrate
   ```
   This creates `Main_DataBase.db` with required tables.

5. **Configure environment (optional):**
   Create a `.env` file:
   ```bash
   SECRET_KEY=your-secret-key-here
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   TELEGRAM_CHAT_ID=your-telegram-chat-id
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build for production (optional):**
   ```bash
   npm run build
   ```

## Running the Application

### Development Mode

1. **Start backend (Terminal 1):**
   ```bash
   python -m backend.app
   ```
   Backend runs on `http://localhost:5000`

2. **Start frontend dev server (Terminal 2):**
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend runs on `http://localhost:3000` (proxy to backend)

### Production Mode

1. **Build frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Start backend (serves built frontend):**
   ```bash
   python -m backend.app
   ```
   Application runs on `http://localhost:5000`

## Usage

### Creating a Campaign

1. **Upload CSV file:**
   - Go to Dashboard
   - Drag-and-drop CSV file or click to browse
   - System auto-detects email column (Email, E-mail, email, etc.)

2. **Configure campaign:**
   - Name: Campaign identifier
   - Provider: MailerSend or Gmail
   - Subject: Email subject line
   - Sender email: Your sender address
   - Batch size: Emails per batch (default: 1)
   - Delay: Seconds between batches (default: 45)
   - Daily limit: Max emails per day (default: 2000)

3. **Provider configuration:**
   - **MailerSend**: Provide API token
   - **Gmail**: Provide App Password (or OAuth credentials)

4. **Email content:**
   - Option A: Paste plain-text vacancies → auto-wrapped into HTML
   - Option B: Upload custom HTML template
   - Option C: Use default template with custom variables

5. **Start campaign:**
   - Click "Start Campaign"
   - Monitor real-time logs in campaign tab
   - View progress (sent/errors) in dashboard

### Template Variables

The template engine supports these Jinja2 placeholders:

- `{{ vacancies }}` - Formatted vacancy text (HTML)
- `{{ cta_subject }}` - Call-to-action subject/heading
- `{{ cta_body }}` - Call-to-action body text (HTML)

### Blacklist Management

- Import unsubscribed/bounced emails via API
- Manual addition via UI
- Auto-filtered during campaign execution

### Telegram Notifications

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in Settings to receive:
- Campaign start notifications
- Batch completion updates
- Error alerts
- Campaign completion summary

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get settings |
| PUT | `/api/settings` | Update settings |
| POST | `/api/campaigns` | Create & start campaign |
| GET | `/api/campaigns` | List all campaigns |
| GET | `/api/campaigns/<id>` | Get campaign details |
| GET | `/api/campaigns/<id>/logs` | Get campaign logs |
| GET | `/api/campaigns/<id>/html` | Download rendered HTML |
| POST | `/api/upload` | Upload CSV file |
| GET | `/api/blacklist` | Get blacklist |
| POST | `/api/blacklist` | Add to blacklist |

### WebSocket Events

- `connect` - Connect to server
- `join_campaign` - Join campaign log room
- `campaign_log` - Receive log messages (level, message, timestamp)

## Rate Limits

### MailerSend
- Automatic handling of 429 (rate limit) and 409 (conflict) responses
- Exponential backoff retry logic
- Configurable max retries (default: 3)

### Gmail
- **90 BCC recipients per email** - automatically batched
- **2,000 emails per day** - auto-pause until reset (00:05 local time)
- Respects SMTP connection limits

## Database Schema

### Tables

- **settings** - Application settings (key, value)
- **campaigns** - Campaign metadata (id, name, provider, status, counts)
- **logs** - Campaign logs (id, campaign_id, ts, level, message)
- **blacklist** - Blacklisted emails (email, reason, added_ts)

## Development

### Running Tests

```bash
pytest
pytest --cov=backend
```

### Code Style

- PEP 8 compliance
- Type hints with mypy
- Minimum 80% test coverage

### Project Status

This is a refactoring from CLI to web application. Current status:

- ✅ Backend infrastructure (Flask, SQLAlchemy, SocketIO)
- ✅ Mailer strategies (MailerSend, Gmail)
- ✅ Template engine
- ✅ Campaign service
- ✅ Basic API endpoints
- ⚠️ Frontend MVP (basic React app - full UI pending)
- ⚠️ Telegram integration (backend ready, needs frontend UI)
- ⚠️ Advanced features (WYSIWYG editor, i18n, dark mode)

## License

Use at your own risk. Ensure compliance with:
- Email sending regulations (CAN-SPAM, GDPR)
- Provider Terms of Service (MailerSend, Gmail)
- Recipient consent requirements

## Support

For issues or questions, please open an issue in the repository.
