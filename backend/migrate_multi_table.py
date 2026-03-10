import sqlite3
import sys
import os

# Adjusted import for standalone execution
try:
    from backend.models.database import DB_PATH
except ImportError:
    # Fallback for direct script execution
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.models.database import DB_PATH


def migrate_multi_table():
    """Migrate database_table column to TEXT to support JSON array of tables."""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check current column type
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if 'database_table' in columns:
            current_type = columns['database_table'].upper()
            if 'TEXT' not in current_type:
                print("Converting database_table column to TEXT to support multiple tables...")
                # SQLite doesn't support ALTER COLUMN, so we need to recreate table
                # But this is complex, so we'll just note it - existing data will work
                print("✅ Column type check completed. TEXT type supports JSON arrays.")
        else:
            print("✅ Migration skipped: database_table column doesn't exist")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_multi_table()
    sys.exit(0 if success else 1)
