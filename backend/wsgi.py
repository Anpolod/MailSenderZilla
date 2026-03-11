"""WSGI entrypoint for production servers (gunicorn/systemd)."""
from backend.app import app, load_environment, bootstrap_application

# Load .env.production/.env and initialize DB state in worker process startup.
load_environment()
bootstrap_application()

# gunicorn entrypoint target: backend.wsgi:application
application = app
