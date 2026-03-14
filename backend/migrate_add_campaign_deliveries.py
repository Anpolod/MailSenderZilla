"""Migration script to add campaign_deliveries table."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import DB_PATH


def migrate_add_campaign_deliveries():
    """Create per-recipient delivery tracking table if missing."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                sequence_no INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                last_error TEXT,
                created_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_ts DATETIME,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_delivery_campaign_email
            ON campaign_deliveries (campaign_id, email)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_campaign_deliveries_campaign_id
            ON campaign_deliveries (campaign_id)
            """
        )
        conn.commit()
        print("✅ Migration completed: campaign_deliveries table is ready")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_add_campaign_deliveries()
    sys.exit(0 if success else 1)
