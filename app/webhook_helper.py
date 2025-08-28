"""
Webhook helper functions for NewBusiness
Sends notifications to other applications when data changes
"""

import requests
import json
from datetime import datetime

def notify_contact_updated(contact):
    """Notify when a contact is updated in NewBusiness"""
    print(f"🔄 WEBHOOK TRIGGER: Contact updated - {contact.first_name} {contact.last_name} ({contact.email})")
    
    # Get related advertisers for brand mapping
    related_advertisers = contact.get_related_advertisers()
    brands_data = []
    
    for advertiser in related_advertisers:
        brands_data.append({
            'id': advertiser.id,  # Using advertiser ID as brand ID for mapping
            'name': advertiser.name
        })
        print(f"   - Associated with advertiser: {advertiser.name}")
    
    webhook_data = {
        'id': contact.agency_crm_id,  # Use the source ID for proper mapping
        'first_name': contact.first_name,
        'last_name': contact.last_name,
        'email': contact.email,
        'phone': contact.phone,
        'linkedin_url': contact.linkedin_url,
        'brands': brands_data,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    print(f"📤 Sending contact update webhook data: {webhook_data}")
    trigger_webhooks('contact.updated', webhook_data)

def trigger_webhooks(event, data):
    """Trigger webhooks for a specific event"""
    from app.models import Webhook, WebhookLog
    import hashlib
    
    print(f"🔍 TRIGGER WEBHOOKS: Event '{event}' triggered")
    
    # Get all active webhooks for this event
    active_webhooks = Webhook.query.filter(Webhook.is_active == True).all()
    webhooks = []
    for webhook in active_webhooks:
        if event in webhook.events:
            webhooks.append(webhook)
    
    print(f"📋 Found {len(webhooks)} active webhooks for event '{event}'")
    
    for webhook in webhooks:
        print(f"📡 Calling webhook: {webhook.url}")
        try:
            payload = json.dumps(data)
            signature = hashlib.sha256(
                f"{webhook.secret}{payload}".encode()
            ).hexdigest()
            
            response = requests.post(
                webhook.url,
                json=data,
                headers={
                    'X-Webhook-Event': event,
                    'X-Webhook-Signature': signature
                },
                timeout=10
            )
            
            print(f"✅ Webhook response: {response.status_code} - {response.text[:200]}")
            
            # Log the webhook call
            log = WebhookLog(
                webhook_id=webhook.id,
                event=event,
                payload=data,
                response_status=response.status_code,
                response_body=response.text[:1000],  # Limit response body size
                triggered_at=datetime.utcnow()
            )
            
            from app import db
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            print(f"❌ Webhook error: {str(e)}")
            # Log the error
            log = WebhookLog(
                webhook_id=webhook.id,
                event=event,
                payload=data,
                response_status=0,
                response_body=f"Error: {str(e)}",
                triggered_at=datetime.utcnow()
            )
            
            from app import db
            db.session.add(log)
            db.session.commit()