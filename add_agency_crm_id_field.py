#!/usr/bin/env python3
"""
Database migration script to add agency_crm_id field to contact table.
This field will track the source contact ID from Agency CRM for reliable contact matching.
"""

import sqlite3
import sys
import os

def update_database():
    """Add agency_crm_id field to contact table"""
    
    # Database path
    db_path = 'instance/media_agency.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Make sure you're running this from the correct directory.")
        return False
    
    try:
        # Create a backup first
        backup_path = 'instance/media_agency.db.backup_agency_id'
        print(f"📋 Creating backup: {backup_path}")
        
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking if agency_crm_id column already exists...")
        cursor.execute("PRAGMA table_info(contact)")
        columns = cursor.fetchall()
        
        # Check if agency_crm_id already exists
        column_exists = any(col[1] == 'agency_crm_id' for col in columns)
        
        if column_exists:
            print("✅ agency_crm_id column already exists - no changes needed")
            return True
        
        print("📝 Adding agency_crm_id column to contact table...")
        
        # Add the new column
        cursor.execute("ALTER TABLE contact ADD COLUMN agency_crm_id INTEGER")
        
        # Commit changes
        conn.commit()
        print("✅ Database updated successfully!")
        print("📊 agency_crm_id column added to contact table")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(contact)")
        columns = cursor.fetchall()
        for col in columns:
            if col[1] == 'agency_crm_id':
                print("✅ Verification: agency_crm_id column was added successfully")
                break
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        print(f"💾 Database backup available at: {backup_path}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration: Adding agency_crm_id to contact table")
    print("=" * 60)
    
    success = update_database()
    
    if success:
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("📝 Contacts can now track their Agency CRM source ID")
    else:
        print("=" * 60)
        print("❌ Migration failed!")
        sys.exit(1)