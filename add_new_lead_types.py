#!/usr/bin/env python3
"""
Add new lead types (get_info and network) to the database.
This script can be run multiple times safely.
"""

import os
import sys
from app import create_app, db
from app.models import Advertiser

def add_new_lead_types():
    """Add new lead types to the database schema."""
    app = create_app()
    
    with app.app_context():
        # The new lead types are automatically supported since lead_status is a string column
        # We just need to verify the database is accessible
        try:
            # Count advertisers by lead status to verify database connection
            lead_counts = db.session.query(
                Advertiser.lead_status, 
                db.func.count(Advertiser.id)
            ).group_by(Advertiser.lead_status).all()
            
            print("Current lead status distribution:")
            for status, count in lead_counts:
                print(f"  {status}: {count}")
            
            # Check if there are any advertisers with the new statuses
            new_statuses = ['get_info', 'network']
            for status in new_statuses:
                count = Advertiser.query.filter_by(lead_status=status).count()
                if count > 0:
                    print(f"\nFound {count} advertisers with '{status}' status")
                else:
                    print(f"\nNo advertisers with '{status}' status yet")
            
            print("\nNew lead types 'get_info' and 'network' are now available for use!")
            print("The application will recognize these new statuses automatically.")
            
        except Exception as e:
            print(f"Error accessing database: {e}")
            sys.exit(1)

if __name__ == '__main__':
    add_new_lead_types()