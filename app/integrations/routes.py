from flask import jsonify, request, current_app
from flask_login import login_required
from app.integrations import integrations_bp
from functools import wraps
from app.models import Advertiser, SpendingData, Contact, Activity, db
from datetime import datetime
import hashlib
import secrets
import json

# Store API keys and webhooks configuration
API_KEYS = {}
WEBHOOK_SECRETS = {}

from flask_wtf import CSRFProtect

def csrf_exempt(f):
    """Decorator to exempt a view from CSRF protection"""
    if not hasattr(f, '_exempt_csrf'):
        f._exempt_csrf = True
    return f

def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature for security"""
    expected = hashlib.sha256(
        f"{secret}{payload}".encode()
    ).hexdigest()
    return secrets.compare_digest(expected, signature)

def verify_api_key():
    """Verify API key from request"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if not api_key or api_key not in API_KEYS:
        return False
    return True

# Webhook receiver endpoints
@integrations_bp.route('/webhook/agency-crm', methods=['POST'])
def webhook_agency_crm():
    """Receive webhooks from agency-crm"""
    
    # Verify signature if configured
    signature = request.headers.get('X-Webhook-Signature')
    if 'agency-crm' in WEBHOOK_SECRETS and signature:
        if not verify_webhook_signature(request.data.decode(), signature, WEBHOOK_SECRETS['agency-crm']):
            return jsonify({'error': 'Invalid signature'}), 401
    
    event = request.headers.get('X-Webhook-Event')
    data = request.json
    
    try:
        if event == 'company.created' or event == 'company.updated':
            # Sync company as advertiser
            sync_company_to_advertiser(data)
            
        elif event == 'brand.created' or event == 'brand.updated':
            # Sync brand as advertiser
            sync_brand_to_advertiser(data)
            
        elif event == 'contact.created':
            # Sync contact
            sync_contact(data)
            
        elif event == 'contact.updated':
            # Update existing contact
            update_contact(data)
            
        elif event == 'invoice.created':
            # Create activity for invoice
            create_invoice_activity(data)
            
        elif event == 'status_update.created':
            # Create activity for status update
            create_status_update_activity(data)
        
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@integrations_bp.route('/webhook/tv-planner', methods=['POST'])
def webhook_tv_planner():
    """Receive webhooks from tv-planner"""
    
    # Verify signature if configured
    signature = request.headers.get('X-Webhook-Signature')
    if 'tv-planner' in WEBHOOK_SECRETS and signature:
        if not verify_webhook_signature(request.data.decode(), signature, WEBHOOK_SECRETS['tv-planner']):
            return jsonify({'error': 'Invalid signature'}), 401
    
    event = request.headers.get('X-Webhook-Event')
    data = request.json
    
    try:
        if event == 'campaign.created' or event == 'campaign.updated':
            # Sync campaign spending data
            sync_campaign_spending(data)
            
        elif event == 'wave.created' or event == 'wave.updated':
            # Update spending data from wave
            update_spending_from_wave(data)
        
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Data synchronization functions
def sync_company_to_advertiser(company_data):
    """Sync company from agency-crm to advertiser in newbusiness"""
    
    # Check if advertiser exists by name
    advertiser = Advertiser.query.filter_by(name=company_data['name']).first()
    
    if not advertiser:
        advertiser = Advertiser(
            name=company_data['name'],
            current_agency='Our Agency',  # Since it's from our CRM
            lead_status='ours'
        )
        db.session.add(advertiser)
    else:
        # Update existing advertiser
        advertiser.lead_status = 'ours'
    
    # Add activity
    activity = Activity(
        advertiser_id=advertiser.id,
        user_id=1,  # System user
        activity_type='note',
        description=f"Company synced from Agency CRM (ID: {company_data.get('id')})",
        created_at=datetime.utcnow()
    )
    db.session.add(activity)
    db.session.commit()

def sync_brand_to_advertiser(brand_data):
    """Sync brand from agency-crm to advertiser in newbusiness"""
    
    # Use format: "Company - Brand" for the advertiser name
    advertiser_name = f"{brand_data.get('company_name', 'Unknown')} - {brand_data['name']}"
    
    advertiser = Advertiser.query.filter_by(name=advertiser_name).first()
    
    if not advertiser:
        advertiser = Advertiser(
            name=advertiser_name,
            current_agency='Our Agency',
            lead_status='ours'
        )
        db.session.add(advertiser)
    
    # Add activity
    activity = Activity(
        advertiser_id=advertiser.id,
        user_id=1,  # System user
        activity_type='note',
        description=f"Brand synced from Agency CRM (Brand ID: {brand_data.get('id')})",
        created_at=datetime.utcnow()
    )
    db.session.add(activity)
    db.session.commit()

def sync_contact(contact_data):
    """Sync contact from agency-crm - one contact with multiple advertiser relationships"""
    
    if not contact_data.get('email'):
        print("❌ No email provided for contact sync")
        return
    
    # Check if contact already exists (across any advertiser)
    existing_contact = Contact.query.filter_by(email=contact_data.get('email')).first()
    
    if existing_contact:
        print(f"📧 Contact already exists: {existing_contact.first_name} {existing_contact.last_name}")
        # Update existing contact and handle new brand relationships
        update_contact(contact_data)
        return
    
    # Create new contact - use first brand as primary advertiser
    brands = contact_data.get('brands', [])
    if not brands:
        print("❌ No brands provided for contact sync")
        return
    
    # Find primary advertiser (first brand)
    primary_brand = brands[0]
    primary_advertiser = Advertiser.query.filter(
        Advertiser.name.contains(primary_brand['name'])
    ).first()
    
    if not primary_advertiser:
        print(f"❌ Primary advertiser not found for brand: {primary_brand['name']}")
        return
    
    # Create the contact with primary advertiser
    contact = Contact(
        advertiser_id=primary_advertiser.id,
        first_name=contact_data.get('first_name', ''),
        last_name=contact_data.get('last_name', ''),
        email=contact_data.get('email'),
        phone=contact_data.get('phone'),
        linkedin_url=contact_data.get('linkedin_url'),
        added_by_id=1,  # System user
        created_at=datetime.utcnow()
    )
    db.session.add(contact)
    db.session.flush()  # Get the contact ID
    
    print(f"✅ Created contact: {contact.first_name} {contact.last_name} (Primary: {primary_advertiser.name})")
    
    # Create activities for all other advertisers to show the relationship
    for brand in brands:
        advertiser = Advertiser.query.filter(
            Advertiser.name.contains(brand['name'])
        ).first()
        
        if advertiser:
            if advertiser.id != primary_advertiser.id:
                # Create relationship activity for other advertisers
                activity = Activity(
                    advertiser_id=advertiser.id,
                    user_id=1,  # System user
                    activity_type='note',
                    description=f"Contact relationship established: {contact.first_name} {contact.last_name}",
                    outcome=f"Contact: {contact.email} | Phone: {contact.phone or 'N/A'}",
                    created_at=datetime.utcnow()
                )
                db.session.add(activity)
                print(f"🔗 Created relationship activity for: {advertiser.name}")
            
            # Create sync activity for primary advertiser
            else:
                activity = Activity(
                    advertiser_id=advertiser.id,
                    user_id=1,  # System user
                    activity_type='note',
                    description=f"Contact synced from Agency CRM: {contact.first_name} {contact.last_name}",
                    outcome=f"New contact added from Agency CRM sync",
                    created_at=datetime.utcnow()
                )
                db.session.add(activity)
    
    db.session.commit()

def update_contact(contact_data):
    """Update existing contact from agency-crm - maintaining single contact with multiple relationships"""
    
    print(f"🔍 Looking for existing contact with email: {contact_data.get('email')}")
    
    if not contact_data.get('email'):
        print("❌ No email provided, cannot update contact")
        return
    
    # Find THE existing contact (should be only one now)
    existing_contact = Contact.query.filter_by(email=contact_data.get('email')).first()
    
    if existing_contact:
        print(f"📧 Found existing contact: {existing_contact.first_name} {existing_contact.last_name}")
        print(f"   Primary advertiser: {existing_contact.advertiser.name}")
        
        # Update the contact information
        existing_contact.first_name = contact_data.get('first_name', existing_contact.first_name)
        existing_contact.last_name = contact_data.get('last_name', existing_contact.last_name) 
        existing_contact.phone = contact_data.get('phone', existing_contact.phone)
        existing_contact.linkedin_url = contact_data.get('linkedin_url', existing_contact.linkedin_url)
        existing_contact.updated_at = datetime.utcnow()
        
        print(f"🔄 Updated contact information")
        
        # Handle brand relationships - create activities for all related advertisers
        for brand in contact_data.get('brands', []):
            advertiser = Advertiser.query.filter(
                Advertiser.name.contains(brand['name'])
            ).first()
            
            if advertiser:
                # Create/update activity for this advertiser relationship
                activity = Activity(
                    advertiser_id=advertiser.id,
                    user_id=1,  # System user
                    activity_type='note',
                    description=f"Contact updated from Agency CRM: {existing_contact.first_name} {existing_contact.last_name}",
                    outcome=f"Contact info synchronized | Email: {existing_contact.email} | Phone: {existing_contact.phone or 'N/A'}",
                    created_at=datetime.utcnow()
                )
                db.session.add(activity)
                
                if advertiser.id == existing_contact.advertiser_id:
                    print(f"✅ Updated primary relationship: {advertiser.name}")
                else:
                    print(f"🔗 Updated related relationship: {advertiser.name}")
        
        print(f"✅ Contact update completed with all brand relationships")
        
    else:
        # No existing contact found, create new one
        print(f"❌ No existing contact found with email '{contact_data.get('email')}'")
        print(f"🔄 Creating new contact")
        sync_contact(contact_data)
        return
    
    db.session.commit()

def create_invoice_activity(invoice_data):
    """Create activity for invoice from agency-crm"""
    
    # Find advertiser by brand name
    advertiser = Advertiser.query.filter(
        Advertiser.name.contains(invoice_data.get('brand_name', ''))
    ).first()
    
    if advertiser:
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=1,  # System user
            activity_type='note',
            description=f"Invoice created: {invoice_data.get('invoice_date')} - "
                       f"Amount: {invoice_data.get('total_amount')} EUR",
            outcome='Invoice logged',
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()

def create_status_update_activity(update_data):
    """Create activity for status update from agency-crm"""
    
    # Find advertiser by brand name
    advertiser = Advertiser.query.filter(
        Advertiser.name.contains(update_data.get('brand_name', ''))
    ).first()
    
    if advertiser:
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=1,  # System user
            activity_type='note',
            description=f"Status Update: {update_data.get('update_text', '')}",
            outcome=f"By: {update_data.get('created_by', 'Unknown')}",
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()

def sync_campaign_spending(campaign_data):
    """Sync campaign spending from tv-planner"""
    
    # This would need proper mapping between campaign names and advertisers
    # For now, we'll use a simple name matching
    advertiser_name = campaign_data.get('name', '').split('-')[0].strip()
    
    if advertiser_name:
        advertiser = Advertiser.query.filter(
            Advertiser.name.contains(advertiser_name)
        ).first()
        
        if advertiser:
            # Get or create spending data for current year
            current_year = datetime.now().year
            spending = SpendingData.query.filter_by(
                advertiser_id=advertiser.id,
                year=current_year
            ).first()
            
            if not spending:
                spending = SpendingData(
                    advertiser_id=advertiser.id,
                    year=current_year
                )
                db.session.add(spending)
            
            # Update TV spending (assuming campaign is TV)
            spending.tv = campaign_data.get('total_spending', 0)
            
            # Create activity
            activity = Activity(
                advertiser_id=advertiser.id,
                user_id=1,
                activity_type='note',
                description=f"TV Campaign synced: {campaign_data.get('name')}",
                outcome=f"Spending: {campaign_data.get('total_spending', 0)} EUR",
                created_at=datetime.utcnow()
            )
            db.session.add(activity)
            db.session.commit()

def update_spending_from_wave(wave_data):
    """Update spending data from tv-planner wave"""
    
    # Similar to campaign sync but for wave-level data
    campaign_name = wave_data.get('campaign_name', '')
    advertiser_name = campaign_name.split('-')[0].strip()
    
    if advertiser_name:
        advertiser = Advertiser.query.filter(
            Advertiser.name.contains(advertiser_name)
        ).first()
        
        if advertiser:
            activity = Activity(
                advertiser_id=advertiser.id,
                user_id=1,
                activity_type='note',
                description=f"TV Wave updated: {wave_data.get('name')}",
                created_at=datetime.utcnow()
            )
            db.session.add(activity)
            db.session.commit()

# API endpoints for pulling data
@integrations_bp.route('/sync/agency-crm', methods=['POST'])
@login_required
def sync_from_agency_crm():
    """Manually trigger sync from agency-crm"""
    
    import requests
    
    # Get configuration from request or use defaults
    api_url = request.json.get('api_url', 'http://localhost:5000/api')
    api_key = request.json.get('api_key', '')
    
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    
    try:
        headers = {'X-API-Key': api_key}
        
        # Sync companies
        response = requests.get(f"{api_url}/companies", headers=headers)
        if response.status_code == 200:
            companies = response.json()
            for company in companies:
                sync_company_to_advertiser(company)
        
        # Sync brands
        response = requests.get(f"{api_url}/brands", headers=headers)
        if response.status_code == 200:
            brands = response.json()
            for brand in brands:
                sync_brand_to_advertiser(brand)
        
        # Sync contacts
        response = requests.get(f"{api_url}/contacts", headers=headers)
        if response.status_code == 200:
            contacts = response.json()
            for contact in contacts:
                sync_contact(contact)
        
        return jsonify({
            'status': 'success',
            'message': 'Data synced from agency-crm'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@integrations_bp.route('/sync/tv-planner', methods=['POST'])
@login_required
def sync_from_tv_planner():
    """Manually trigger sync from tv-planner"""
    
    import requests
    
    # Get configuration from request or use defaults
    api_url = request.json.get('api_url', 'http://localhost:5004/api')
    api_key = request.json.get('api_key', '')
    
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    
    try:
        headers = {'X-API-Key': api_key}
        
        # Sync campaigns
        response = requests.get(f"{api_url}/campaigns", headers=headers)
        if response.status_code == 200:
            campaigns = response.json()
            for campaign in campaigns:
                # Get spending data for each campaign
                spending_response = requests.get(
                    f"{api_url}/campaigns/{campaign['id']}/spending",
                    headers=headers
                )
                if spending_response.status_code == 200:
                    campaign['total_spending'] = spending_response.json().get('total_spending', 0)
                sync_campaign_spending(campaign)
        
        return jsonify({
            'status': 'success',
            'message': 'Data synced from tv-planner'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500