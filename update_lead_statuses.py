#!/usr/bin/env python3
"""
Script to update existing lead statuses to the new system.
Run this once to migrate existing data.
"""

from app import create_app, db
from app.models import Advertiser
from app.utils import update_lead_statuses_by_agency

def migrate_lead_statuses():
    app = create_app()
    
    with app.app_context():
        print("Migrating lead statuses to new system...")
        
        # First, update all existing 'cold' to 'non_qualified' as default
        cold_count = Advertiser.query.filter_by(lead_status='cold').update({'lead_status': 'non_qualified'})
        print(f"Updated {cold_count} 'cold' leads to 'non_qualified'")
        
        # Update 'not_possible' to 'non_market'
        not_possible_count = Advertiser.query.filter_by(lead_status='not_possible').update({'lead_status': 'non_market'})
        print(f"Updated {not_possible_count} 'not_possible' leads to 'non_market'")
        
        # Commit these changes first
        db.session.commit()
        
        # Now run the agency-based status update
        updated_count = update_lead_statuses_by_agency()
        print(f"Updated {updated_count} lead statuses based on agency assignments")
        
        # Show final status distribution
        status_counts = db.session.query(
            Advertiser.lead_status,
            db.func.count(Advertiser.id)
        ).group_by(Advertiser.lead_status).all()
        
        print("\nFinal lead status distribution:")
        for status, count in status_counts:
            print(f"  {status}: {count}")

if __name__ == '__main__':
    migrate_lead_statuses()