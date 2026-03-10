"""Database migration script."""
from backend.models.database import init_db, get_session, Settings
import os
import sys


def run_migration():
    """Run database migration."""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 fallback
            pass
    
    try:
        print("🔄 Running database migration...")
    except UnicodeEncodeError:
        print("Running database migration...")
    
    # Initialize database (creates tables if not exist)
    init_db()
    
    # Set default settings if not exist
    session = get_session()
    try:
        # Check if settings exist
        telegram_token = session.query(Settings).filter_by(key='telegram_bot_token').first()
        if not telegram_token:
            session.add(Settings(key='telegram_bot_token', value=''))
        
        telegram_chat_id = session.query(Settings).filter_by(key='telegram_chat_id').first()
        if not telegram_chat_id:
            session.add(Settings(key='telegram_chat_id', value=''))
        
        mailersend_api_token = session.query(Settings).filter_by(key='mailersend_api_token').first()
        if not mailersend_api_token:
            session.add(Settings(key='mailersend_api_token', value=''))
        
        gmail_app_password = session.query(Settings).filter_by(key='gmail_app_password').first()
        if not gmail_app_password:
            session.add(Settings(key='gmail_app_password', value=''))
        
        session.commit()
        try:
            print("✅ Migration completed successfully!")
        except UnicodeEncodeError:
            print("Migration completed successfully!")
    except Exception as e:
        session.rollback()
        try:
            print(f"❌ Migration error: {e}")
        except UnicodeEncodeError:
            print(f"Migration error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    run_migration()

