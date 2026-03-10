"""Migration script to add html_body and vacancies_text columns to campaigns table."""
import sqlite3
import sys
import os

# Fix Unicode encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Get DB path (same logic as database.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'Main_DataBase.db')


def migrate_add_email_content():
    """Add html_body and vacancies_text columns to campaigns table if they don't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [row[1] for row in cursor.fetchall()]
        
        changes_made = False
        
        if 'html_body' not in columns:
            print("Adding html_body column to campaigns table...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN html_body TEXT")
            changes_made = True
        
        if 'vacancies_text' not in columns:
            print("Adding vacancies_text column to campaigns table...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN vacancies_text TEXT")
            changes_made = True
        
        if changes_made:
            conn.commit()
            try:
                print("✅ Migration completed: Email content columns added")
            except UnicodeEncodeError:
                print("Migration completed: Email content columns added")
        else:
            try:
                print("✅ Migration skipped: Email content columns already exist")
            except UnicodeEncodeError:
                print("Migration skipped: Email content columns already exist")
        
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
    success = migrate_add_email_content()
    sys.exit(0 if success else 1)
