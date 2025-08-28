#!/usr/bin/env python3
"""
Database migration script to make contact.advertiser_id nullable.
This allows contacts to exist without being associated to any advertiser.
"""

import sqlite3
import sys
import os

def update_database():
    """Update the database to make contact.advertiser_id nullable"""
    
    # Database path
    db_path = 'instance/media_agency.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Make sure you're running this from the correct directory.")
        return False
    
    try:
        # Create a backup first
        backup_path = 'agency_lead_management.db.backup'
        print(f"📋 Creating backup: {backup_path}")
        
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current contact table structure...")
        cursor.execute("PRAGMA table_info(contact)")
        columns = cursor.fetchall()
        
        # Check if advertiser_id is currently NOT NULL
        advertiser_col = None
        for col in columns:
            if col[1] == 'advertiser_id':
                advertiser_col = col
                break
        
        if not advertiser_col:
            print("❌ advertiser_id column not found in contact table")
            return False
        
        if advertiser_col[3] == 0:  # notnull = 0 means it's already nullable
            print("✅ contact.advertiser_id is already nullable - no changes needed")
            return True
        
        print("📝 Making contact.advertiser_id nullable...")
        
        # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
        # Step 1: Create new table with nullable advertiser_id
        cursor.execute("""
            CREATE TABLE contact_new (
                id INTEGER PRIMARY KEY,
                advertiser_id INTEGER,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(200),
                phone VARCHAR(50),
                linkedin_url VARCHAR(500),
                added_by_id INTEGER NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (advertiser_id) REFERENCES advertiser(id),
                FOREIGN KEY (added_by_id) REFERENCES user(id)
            )
        """)
        
        # Step 2: Copy data from old table to new table
        cursor.execute("""
            INSERT INTO contact_new 
            SELECT id, advertiser_id, first_name, last_name, email, phone, 
                   linkedin_url, added_by_id, created_at, updated_at
            FROM contact
        """)
        
        # Step 3: Drop old table and rename new table
        cursor.execute("DROP TABLE contact")
        cursor.execute("ALTER TABLE contact_new RENAME TO contact")
        
        # Commit changes
        conn.commit()
        print("✅ Database updated successfully!")
        print("📊 contact.advertiser_id is now nullable")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(contact)")
        columns = cursor.fetchall()
        for col in columns:
            if col[1] == 'advertiser_id':
                if col[3] == 0:  # notnull = 0 means nullable
                    print("✅ Verification: advertiser_id is now nullable")
                else:
                    print("❌ Verification failed: advertiser_id is still NOT NULL")
                break
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        print(f"💾 Database backup available at: {backup_path}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration: Making contact.advertiser_id nullable")
    print("=" * 60)
    
    success = update_database()
    
    if success:
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("📝 Contacts can now be saved without advertiser associations")
    else:
        print("=" * 60)
        print("❌ Migration failed!")
        sys.exit(1)