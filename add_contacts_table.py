#!/usr/bin/env python3
"""
Script to add contacts table and update activities table.
"""

from app import create_app, db
from sqlalchemy import text

def add_contacts_functionality():
    app = create_app()
    
    with app.app_context():
        print("Adding contacts functionality...")
        
        try:
            # Create contacts table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS contact (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    advertiser_id INTEGER NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    email VARCHAR(200),
                    phone VARCHAR(50),
                    linkedin_url VARCHAR(500),
                    added_by_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (advertiser_id) REFERENCES advertiser (id),
                    FOREIGN KEY (added_by_id) REFERENCES user (id)
                )
            """))
            print("✓ Created contact table")
            
            # Add contact_id column to activity table
            db.session.execute(text("""
                ALTER TABLE activity 
                ADD COLUMN contact_id INTEGER REFERENCES contact(id)
            """))
            print("✓ Added contact_id column to activity table")
            
            db.session.commit()
            print("✓ Database updated successfully")
            
        except Exception as e:
            db.session.rollback()
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Tables/columns already exist")
            else:
                print(f"Error updating database: {e}")

if __name__ == '__main__':
    add_contacts_functionality()