#!/usr/bin/env python3
"""
Database migration script to add webhook and webhook_log tables.
This enables NewBusiness to send outgoing webhooks to other applications.
"""

import sqlite3
import sys
import os

def update_database():
    """Add webhook and webhook_log tables"""
    
    # Database path
    db_path = 'instance/media_agency.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Make sure you're running this from the correct directory.")
        return False
    
    try:
        # Create a backup first
        backup_path = 'instance/media_agency.db.backup_webhooks'
        print(f"📋 Creating backup: {backup_path}")
        
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking if webhook tables already exist...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('webhook', 'webhook_log')")
        existing_tables = cursor.fetchall()
        existing_table_names = [table[0] for table in existing_tables]
        
        if 'webhook' in existing_table_names and 'webhook_log' in existing_table_names:
            print("✅ Webhook tables already exist - no changes needed")
            return True
        
        print("📝 Creating webhook tables...")
        
        # Create webhook table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook (
                id INTEGER PRIMARY KEY,
                url VARCHAR(500) NOT NULL,
                events JSON NOT NULL,
                secret VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create webhook_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_log (
                id INTEGER PRIMARY KEY,
                webhook_id INTEGER NOT NULL,
                event VARCHAR(100) NOT NULL,
                payload JSON,
                response_status INTEGER,
                response_body TEXT,
                triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (webhook_id) REFERENCES webhook(id)
            )
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Database updated successfully!")
        print("📊 Webhook tables created")
        
        # Verify the tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('webhook', 'webhook_log')")
        new_tables = cursor.fetchall()
        new_table_names = [table[0] for table in new_tables]
        
        if 'webhook' in new_table_names and 'webhook_log' in new_table_names:
            print("✅ Verification: Both webhook tables were created successfully")
        else:
            print("❌ Verification failed: Not all webhook tables were created")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        print(f"💾 Database backup available at: {backup_path}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration: Adding webhook tables")
    print("=" * 60)
    
    success = update_database()
    
    if success:
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("📝 NewBusiness can now send outgoing webhooks")
    else:
        print("=" * 60)
        print("❌ Migration failed!")
        sys.exit(1)