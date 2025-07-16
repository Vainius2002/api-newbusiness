#!/usr/bin/env python3
"""
Script to add net_total column to spending_data table.
"""

from app import create_app, db
from sqlalchemy import text

def add_net_spending_column():
    app = create_app()
    
    with app.app_context():
        print("Adding net_total column to spending_data table...")
        
        try:
            # Add the column if it doesn't exist
            db.session.execute(text("""
                ALTER TABLE spending_data 
                ADD COLUMN net_total REAL
            """))
            db.session.commit()
            print("Successfully added net_total column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column net_total already exists")
            else:
                print(f"Error adding column: {e}")
                db.session.rollback()

if __name__ == '__main__':
    add_net_spending_column()