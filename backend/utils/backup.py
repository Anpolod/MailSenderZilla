"""Utilities for database backup."""
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from backend.models.database import DB_PATH


def _default_backup_dir() -> Path:
    """Return canonical backup directory path."""
    return Path(DB_PATH).parent / 'backups'


def _resolve_backup_path(backup_path: str, backup_dir: str = None) -> Path:
    """
    Resolve backup path safely.

    Accepts either a filename (preferred) or absolute path inside backup dir.
    """
    base_dir = Path(backup_dir) if backup_dir is not None else _default_backup_dir()
    base_dir = base_dir.resolve()
    candidate = Path(backup_path)

    # For relative input, keep only filename to avoid path traversal attempts.
    if not candidate.is_absolute():
        candidate = base_dir / candidate.name

    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        raise Exception("Backup path is outside allowed backups directory")

    return resolved


def create_backup(backup_dir: str = None) -> str:
    """
    Create a backup of the database.
    
    Args:
        backup_dir: Directory to save backup (default: backups/ in project root)
    
    Returns:
        Path to created backup file
    """
    if backup_dir is None:
        backup_dir = _default_backup_dir()
    
    # Create backup directory if it doesn't exist
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'Main_DataBase_backup_{timestamp}.db'
    backup_path = backup_dir / backup_filename
    
    try:
        # Copy database file
        shutil.copy2(DB_PATH, backup_path)
        return str(backup_path)
    except Exception as e:
        raise Exception(f"Failed to create backup: {str(e)}")


def list_backups(backup_dir: str = None) -> list:
    """
    List all backup files.
    
    Args:
        backup_dir: Directory to search for backups
    
    Returns:
        List of backup file info dicts with path, size, and date
    """
    if backup_dir is None:
        backup_dir = _default_backup_dir()
    
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    
    backups = []
    for backup_file in backup_dir.glob('Main_DataBase_backup_*.db'):
        try:
            stat = backup_file.stat()
            backups.append({
                'filename': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'size_mb': round(stat.st_size / (1024 * 1024), 2)
            })
        except Exception:
            continue
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


def restore_backup(backup_path: str) -> bool:
    """
    Restore database from backup.
    
    Args:
        backup_path: Path to backup file
    
    Returns:
        True if successful
    """
    backup_path = _resolve_backup_path(backup_path)
    
    if not backup_path.exists():
        raise Exception(f"Backup file not found: {backup_path}")
    
    # Verify backup is valid SQLite database
    try:
        conn = sqlite3.connect(str(backup_path))
        conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
        conn.close()
    except Exception as e:
        raise Exception(f"Invalid backup file: {str(e)}")
    
    # Create a safety backup of current database before restore
    try:
        safety_backup_path = str(DB_PATH) + f'.pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(DB_PATH, safety_backup_path)
    except Exception:
        pass  # If we can't create safety backup, continue anyway
    
    try:
        # Replace current database with backup
        shutil.copy2(backup_path, DB_PATH)
        return True
    except Exception as e:
        raise Exception(f"Failed to restore backup: {str(e)}")


def delete_backup(backup_path: str) -> bool:
    """
    Delete a backup file.
    
    Args:
        backup_path: Path to backup file
    
    Returns:
        True if successful
    """
    try:
        resolved_path = _resolve_backup_path(backup_path)
        resolved_path.unlink()
        return True
    except Exception as e:
        raise Exception(f"Failed to delete backup: {str(e)}")
