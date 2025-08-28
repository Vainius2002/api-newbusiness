#!/usr/bin/env python3
"""
Setup script for bidirectional synchronization between NewBusiness and Agency CRM.
Creates webhook configuration in NewBusiness to notify Agency CRM of contact updates.
"""

import secrets
import sys
import os

def setup_webhook():
    """Create webhook configuration in NewBusiness"""
    
    try:
        # Import Flask app and models
        sys.path.append(os.path.dirname(__file__))
        from app import create_app, db
        from app.models import Webhook
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Checking existing webhook configuration...")
            
            # Check if webhook already exists
            webhook_url = "http://localhost:5000/api/webhook/newbusiness"
            existing_webhook = Webhook.query.filter_by(url=webhook_url).first()
            
            if existing_webhook:
                print(f"✅ Webhook already exists: {webhook_url}")
                print(f"   Events: {existing_webhook.events}")
                print(f"   Active: {existing_webhook.is_active}")
                return True
            
            print("📝 Creating new webhook configuration...")
            
            # Generate a secure secret
            webhook_secret = secrets.token_urlsafe(32)
            
            # Create webhook
            webhook = Webhook(
                url=webhook_url,
                events=['contact.updated'],
                secret=webhook_secret,
                is_active=True
            )
            
            db.session.add(webhook)
            db.session.commit()
            
            print("✅ Webhook created successfully!")
            print(f"   URL: {webhook_url}")
            print(f"   Events: ['contact.updated']")
            print(f"   Secret: {webhook_secret}")
            print(f"   Active: True")
            print()
            print("🔧 Next steps:")
            print("1. Make sure Agency CRM is running on port 5000")
            print("2. Test by editing a contact in NewBusiness")
            print("3. Check that the contact updates in Agency CRM")
            
            return True
            
    except Exception as e:
        print(f"❌ Error setting up webhook: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up bidirectional sync: NewBusiness → Agency CRM")
    print("=" * 60)
    
    success = setup_webhook()
    
    if success:
        print("=" * 60)
        print("✅ Bidirectional sync setup completed!")
        print("📝 NewBusiness will now notify Agency CRM of contact updates")
    else:
        print("=" * 60)
        print("❌ Setup failed!")
        sys.exit(1)