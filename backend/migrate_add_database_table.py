"""Migration script to add database_table column to campaigns table."""
import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import DB_PATH


def migrate_add_database_table():
    """Add database_table column to campaigns table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'database_table' not in columns:
            print("Adding database_table column to campaigns table...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN database_table TEXT")
            conn.commit()
            print("✅ Migration completed: database_table column added")
        else:
            print("✅ Migration skipped: database_table column already exists")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_add_database_table()
    sys.exit(0 if success else 1)
