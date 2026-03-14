"""Helpers for campaign log files."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_LOG_DIR = Path(
    os.getenv('CAMPAIGN_LOG_DIR', PROJECT_ROOT / 'logs' / 'campaigns')
).resolve()

LOG_LINE_RE = re.compile(
    r'^\[(?P<timestamp>[^\]]+)\]\[(?P<level>[A-Z]+)\]\s?(?P<message>.*)$'
)


def ensure_campaign_log_dir() -> Path:
    """Ensure campaign log directory exists."""
    CAMPAIGN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return CAMPAIGN_LOG_DIR


def get_campaign_log_path(campaign_id: int) -> Path:
    """Return log file path for a campaign."""
    ensure_campaign_log_dir()
    return CAMPAIGN_LOG_DIR / f'campaign_{campaign_id}.log'


def append_campaign_log(campaign_id: int, level: str, message: str, ts: Optional[datetime] = None) -> Path:
    """Append one formatted log line to the campaign file."""
    timestamp = (ts or datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')
    path = get_campaign_log_path(campaign_id)
    safe_message = (message or '').replace('\r\n', '\n').replace('\r', '\n')
    with path.open('a', encoding='utf-8') as fh:
        for line in safe_message.split('\n'):
            fh.write(f'[{timestamp}][{(level or "INFO").upper()}] {line}\n')
    return path


def parse_log_line(line: str) -> dict:
    """Parse one log line into structured data."""
    raw = line.rstrip('\n')
    match = LOG_LINE_RE.match(raw)
    if not match:
        return {
            'timestamp': None,
            'level': 'INFO',
            'message': raw,
            'raw': raw,
        }
    return {
        'timestamp': match.group('timestamp'),
        'level': match.group('level'),
        'message': match.group('message'),
        'raw': raw,
    }


def read_campaign_log_lines(campaign_id: int, limit: Optional[int] = None) -> list[dict]:
    """Read campaign log file lines."""
    path = get_campaign_log_path(campaign_id)
    if not path.exists():
        return []

    with path.open('r', encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()

    if limit is not None:
        lines = lines[-max(int(limit), 0):]

    return [parse_log_line(line) for line in lines]


def read_campaign_log_text(campaign_id: int) -> str:
    """Read full campaign log text."""
    path = get_campaign_log_path(campaign_id)
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='replace')


def delete_campaign_log_file(campaign_id: int) -> None:
    """Remove campaign log file if it exists."""
    path = get_campaign_log_path(campaign_id)
    if path.exists():
        path.unlink()
