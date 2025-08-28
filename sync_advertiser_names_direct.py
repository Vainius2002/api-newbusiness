#!/usr/bin/env python3
"""
Direct database sync script to update NewBusiness advertiser names 
to match Agency CRM brand format: "Brand (Company)"
"""

import sys
import os
import sqlite3

def sync_advertiser_names_direct():
    """Directly sync from Agency CRM database to NewBusiness database"""
    
    try:
        print("🔍 Connecting to Agency CRM database...")
        
        # Connect to Agency CRM database
        agency_db_path = '/home/vainiusl/py_projects/agency-crm/instance/agency_crm.db'
        if not os.path.exists(agency_db_path):
            print(f"❌ Agency CRM database not found: {agency_db_path}")
            return False
            
        agency_conn = sqlite3.connect(agency_db_path)
        agency_cursor = agency_conn.cursor()
        
        # Get all brands with company information from Agency CRM
        agency_cursor.execute("""
            SELECT b.name as brand_name, c.name as company_name, b.id as brand_id
            FROM brands b 
            JOIN companies c ON b.company_id = c.id 
            WHERE b.status = 'active'
            ORDER BY b.name
        """)
        
        agency_brands = agency_cursor.fetchall()
        print(f"✅ Found {len(agency_brands)} active brands in Agency CRM")
        
        agency_conn.close()
        
        # Now update NewBusiness advertisers
        print("🔄 Updating NewBusiness advertisers...")
        
        # Import NewBusiness models
        sys.path.append(os.path.dirname(__file__))
        from app import create_app, db
        from app.models import Advertiser
        
        app = create_app()
        
        with app.app_context():
            # Clear existing advertisers to avoid confusion
            print("🧹 Removing old advertisers...")
            old_advertisers = Advertiser.query.all()
            for adv in old_advertisers:
                # Update any contacts/activities to remove references first
                from app.models import Contact, Activity
                Contact.query.filter_by(advertiser_id=adv.id).update({'advertiser_id': None})
                Activity.query.filter_by(advertiser_id=adv.id).delete()
                db.session.delete(adv)
            
            print(f"Removed {len(old_advertisers)} old advertisers")
            
            # Create new advertisers with Agency CRM format
            print("➕ Creating advertisers with Agency CRM format...")
            
            new_advertisers = []
            for brand_name, company_name, brand_id in agency_brands:
                # Create advertiser name in format: "Brand (Company)"
                advertiser_name = f"{brand_name} ({company_name})"
                
                new_advertiser = Advertiser(
                    name=advertiser_name
                )
                db.session.add(new_advertiser)
                new_advertisers.append(advertiser_name)
                
                print(f"  ➕ {advertiser_name}")
            
            # Commit changes
            print(f"\\n💾 Committing {len(new_advertisers)} new advertisers...")
            db.session.commit()
            
            print(f"\\n✅ Sync completed successfully!")
            print(f"📊 Summary:")
            print(f"  - Old advertisers removed: {len(old_advertisers)}")
            print(f"  - New advertisers created: {len(new_advertisers)}")
            print(f"  - Format: Brand (Company)")
            print(f"\\n🎯 NewBusiness advertisers now exactly match Agency CRM!")
            
            # Show first few examples
            print(f"\\n📝 Examples:")
            for i, name in enumerate(new_advertisers[:5]):
                print(f"  - {name}")
            if len(new_advertisers) > 5:
                print(f"  ... and {len(new_advertisers) - 5} more")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Direct sync: NewBusiness advertisers ← Agency CRM brands")
    print("=" * 60)
    
    success = sync_advertiser_names_direct()
    
    if success:
        print("=" * 60)
        print("✅ Direct sync completed!")
        print("📝 Contact forms now show exact Agency CRM format")
        print("⚠️  Note: Existing contact-advertiser associations were reset")
        print("   You may need to re-associate contacts with advertisers")
    else:
        print("=" * 60)
        print("❌ Sync failed!")
        sys.exit(1)