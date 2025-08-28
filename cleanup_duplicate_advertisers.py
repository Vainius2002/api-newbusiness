#!/usr/bin/env python3
"""
Cleanup script to consolidate duplicate/similar advertisers in NewBusiness.
This will merge company names and brand names into single advertiser records.
"""

import sys
import os
from collections import defaultdict

def cleanup_advertisers():
    """Cleanup and consolidate duplicate advertisers"""
    
    try:
        # Import Flask app and models
        sys.path.append(os.path.dirname(__file__))
        from app import create_app, db
        from app.models import Advertiser, Contact, Activity
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Analyzing advertiser duplicates...")
            
            advertisers = Advertiser.query.all()
            print(f"Found {len(advertisers)} total advertisers")
            
            # Group similar advertisers (company vs brand names)
            groups = defaultdict(list)
            
            for adv in advertisers:
                # Create a key for grouping - remove common suffixes and clean name
                clean_name = adv.name.replace(', UAB', '').replace(' UAB', '').replace(' SIA', '').replace(' AB', '').replace(' OU', '').strip()
                
                # Group by first significant word
                key_words = clean_name.split()[0].lower()
                groups[key_words].append(adv)
            
            # Find groups with multiple entries (potential duplicates)
            duplicates_found = 0
            contacts_updated = 0
            activities_updated = 0
            advertisers_removed = 0
            
            for key, group_advertisers in groups.items():
                if len(group_advertisers) > 1:
                    print(f"\\n📋 Group '{key}' has {len(group_advertisers)} advertisers:")
                    for adv in group_advertisers:
                        print(f"  - {adv.name} (ID: {adv.id})")
                    
                    # Sort by preference: prefer company names (with UAB, SIA, etc.)
                    # These are more complete and official
                    def sort_preference(adv):
                        name = adv.name.upper()
                        # Prefer full company names
                        if any(suffix in name for suffix in [', UAB', ' UAB', ' SIA', ' AB', ' OU']):
                            return 0  # Highest priority
                        # Then brand names
                        return 1
                    
                    group_advertisers.sort(key=sort_preference)
                    primary = group_advertisers[0]
                    duplicates = group_advertisers[1:]
                    
                    print(f"  ✅ Keeping: {primary.name} (ID: {primary.id})")
                    print(f"  🗑️  Removing: {[f'{d.name} (ID: {d.id})' for d in duplicates]}")
                    
                    # Update all references to point to the primary advertiser
                    for duplicate in duplicates:
                        # Update contacts that use this advertiser as primary
                        contacts = Contact.query.filter_by(advertiser_id=duplicate.id).all()
                        for contact in contacts:
                            contact.advertiser_id = primary.id
                            contacts_updated += 1
                            print(f"    📞 Updated contact: {contact.first_name} {contact.last_name}")
                        
                        # Update activities that reference this advertiser
                        activities = Activity.query.filter_by(advertiser_id=duplicate.id).all()
                        for activity in activities:
                            activity.advertiser_id = primary.id
                            activities_updated += 1
                        
                        # Delete the duplicate advertiser
                        db.session.delete(duplicate)
                        advertisers_removed += 1
                    
                    duplicates_found += len(duplicates)
            
            if duplicates_found > 0:
                print(f"\\n💾 Committing changes...")
                db.session.commit()
                
                print(f"\\n✅ Cleanup completed successfully!")
                print(f"📊 Summary:")
                print(f"  - Duplicate advertisers removed: {advertisers_removed}")
                print(f"  - Contacts updated: {contacts_updated}")
                print(f"  - Activities updated: {activities_updated}")
                print(f"  - Total advertisers now: {len(advertisers) - advertisers_removed}")
            else:
                print("\\n✅ No significant duplicates found to cleanup")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting advertiser cleanup: Consolidating duplicates")
    print("=" * 60)
    
    success = cleanup_advertisers()
    
    if success:
        print("=" * 60)
        print("✅ Advertiser cleanup completed!")
        print("📝 Contact form should now show clean advertiser list")
    else:
        print("=" * 60)
        print("❌ Cleanup failed!")
        sys.exit(1)