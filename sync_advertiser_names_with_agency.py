#!/usr/bin/env python3
"""
Script to sync NewBusiness advertiser names with Agency CRM brand format.
This will make advertiser names identical to Agency CRM: "Brand (Company)"
"""

import sys
import os
import requests

def sync_advertiser_names():
    """Sync NewBusiness advertisers with Agency CRM brand names"""
    
    try:
        # Import NewBusiness models
        sys.path.append(os.path.dirname(__file__))
        from app import create_app, db
        from app.models import Advertiser
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Fetching brands from Agency CRM...")
            
            # Get all brands from Agency CRM API
            try:
                response = requests.get('http://localhost:5000/api/brands', timeout=10)
                if response.status_code != 200:
                    print(f"❌ Failed to fetch brands from Agency CRM: {response.status_code}")
                    return False
                
                agency_brands = response.json()
                print(f"✅ Found {len(agency_brands)} brands in Agency CRM")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error connecting to Agency CRM: {e}")
                print("Make sure Agency CRM is running on port 5000")
                return False
            
            print("\\n🔄 Updating NewBusiness advertiser names...")
            
            # Get current advertisers
            current_advertisers = Advertiser.query.all()
            print(f"Found {len(current_advertisers)} current advertisers in NewBusiness")
            
            # Create a mapping of company names to brand info for matching
            company_to_brands = {}
            for brand in agency_brands:
                company_name = brand.get('company_name', '')
                if company_name:
                    if company_name not in company_to_brands:
                        company_to_brands[company_name] = []
                    company_to_brands[company_name].append(brand)
            
            updated_count = 0
            new_advertisers = []
            
            # Update existing advertisers with proper brand format
            for advertiser in current_advertisers:
                current_name = advertiser.name
                
                # Try to find matching brand(s) for this advertiser
                matched_brand = None
                
                # Direct company match
                if current_name in company_to_brands:
                    # Company has multiple brands, pick the first one as primary
                    matched_brand = company_to_brands[current_name][0]
                    print(f"📍 Direct match: {current_name}")
                
                # Partial company match
                if not matched_brand:
                    for company_name, brands in company_to_brands.items():
                        if current_name.lower() in company_name.lower() or company_name.lower() in current_name.lower():
                            matched_brand = brands[0]  # Pick first brand
                            print(f"🔍 Partial match: {current_name} → {company_name}")
                            break
                
                if matched_brand:
                    # Update to Agency CRM format: "Brand (Company)"
                    new_name = f"{matched_brand['name']} ({matched_brand['company_name']})"
                    
                    if new_name != current_name:
                        print(f"  ✏️  {current_name} → {new_name}")
                        advertiser.name = new_name
                        updated_count += 1
                    else:
                        print(f"  ✅ {current_name} (already correct)")
                else:
                    print(f"  ⚠️  No match found for: {current_name}")
            
            # Add any missing brands as new advertisers
            print("\\n🆕 Checking for missing brands...")
            existing_names = {adv.name for adv in current_advertisers}
            
            for brand in agency_brands:
                expected_name = f"{brand['name']} ({brand['company_name']})"
                if expected_name not in existing_names:
                    print(f"  ➕ Adding: {expected_name}")
                    new_advertiser = Advertiser(
                        name=expected_name,
                        status='active'
                    )
                    db.session.add(new_advertiser)
                    new_advertisers.append(expected_name)
            
            # Commit all changes
            print(f"\\n💾 Committing changes...")
            db.session.commit()
            
            print(f"\\n✅ Sync completed successfully!")
            print(f"📊 Summary:")
            print(f"  - Advertisers updated: {updated_count}")
            print(f"  - New advertisers added: {len(new_advertisers)}")
            print(f"  - Total advertisers now: {len(current_advertisers) + len(new_advertisers)}")
            print(f"\\n🎯 NewBusiness advertisers now match Agency CRM format!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Syncing NewBusiness advertiser names with Agency CRM format")
    print("=" * 60)
    
    success = sync_advertiser_names()
    
    if success:
        print("=" * 60)
        print("✅ Advertiser name sync completed!")
        print("📝 Contact forms now show: Brand (Company) format")
    else:
        print("=" * 60)
        print("❌ Sync failed!")
        sys.exit(1)