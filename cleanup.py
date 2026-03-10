"""Script to clean up cache files and temporary files."""
import os
import shutil
import sys
from pathlib import Path

# Fix Unicode encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Files and directories to remove
CLEANUP_ITEMS = [
    # Python cache (exclude .venv - it's managed separately)
    "backend/**/__pycache__",
    "backend/**/*.pyc",
    "backend/**/*.pyo",
    "**/.Python",
    
    # Logs (already in .gitignore but remove if present)
    "*.log",
    "._*.log",
    
    # IDE
    ".vscode",
    ".idea",
    "**/*.swp",
    "**/*.swo",
    "**/*~",
    
    # OS (exclude node_modules - too many files)
    "**/.DS_Store",
    "**/Thumbs.db",
    
    # Testing
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    
    # Old build artifacts (keep dist for production)
    "build",
    "*.egg-info",
]

def cleanup():
    """Remove cache and temporary files."""
    project_root = Path(__file__).parent
    removed = []
    errors = []
    
    try:
        print("Starting cleanup...")
    except UnicodeEncodeError:
        print("Starting cleanup...")
    
    for pattern in CLEANUP_ITEMS:
        matches = list(project_root.glob(pattern))
        for item in matches:
            try:
                if item.is_file():
                    item.unlink()
                    removed.append(str(item.relative_to(project_root)))
                    try:
                        print(f"  Removed file: {item.relative_to(project_root)}")
                    except UnicodeEncodeError:
                        pass
                elif item.is_dir():
                    shutil.rmtree(item)
                    removed.append(str(item.relative_to(project_root)) + "/")
                    try:
                        print(f"  Removed directory: {item.relative_to(project_root)}/")
                    except UnicodeEncodeError:
                        pass
            except Exception as e:
                errors.append(f"  Failed to remove {item}: {e}")
    
    try:
        print(f"\nCleanup complete!")
        print(f"   Removed: {len(removed)} items")
        if errors:
            print(f"   Errors: {len(errors)} items")
            for error in errors:
                print(error)
        else:
            print("   No errors")
    except UnicodeEncodeError:
        print(f"\nCleanup complete! Removed {len(removed)} items")

if __name__ == '__main__':
    cleanup()
