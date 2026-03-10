"""Migration script to add templates table."""
import sqlite3
import sys
import os

# Fix Unicode encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Get DB path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'Main_DataBase.db')


def migrate_add_templates():
    """Add templates table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='templates'
        """)
        
        if cursor.fetchone():
            try:
                print("✅ Migration skipped: Templates table already exists")
            except UnicodeEncodeError:
                print("Migration skipped: Templates table already exists")
            conn.close()
            return True
        
        # Create templates table
        cursor.execute("""
            CREATE TABLE templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                html_body TEXT,
                vacancies_text TEXT,
                created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        try:
            print("✅ Migration completed: Templates table created")
        except UnicodeEncodeError:
            print("Migration completed: Templates table created")
        
        conn.close()
        return True
    except Exception as e:
        try:
            print(f"❌ Migration error: {e}")
        except UnicodeEncodeError:
            print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_add_templates()
    sys.exit(0 if success else 1)
