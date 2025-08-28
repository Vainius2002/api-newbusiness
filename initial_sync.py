#!/usr/bin/env python
"""
Initial data synchronization script for NewBusiness
Pulls all existing data from Agency CRM and TV Planner
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Advertiser, SpendingData, Contact, Activity, User
from datetime import datetime
import requests
import json

# Import configuration
try:
    import integration_config as config
except ImportError:
    print("Error: integration_config.py not found. Run setup_integration.py first.")
    sys.exit(1)

def sync_all_from_agency_crm():
    """Pull all existing data from Agency CRM"""
    print("\n=== Syncing from Agency CRM ===")
    
    base_url = config.AGENCY_CRM_API_URL
    headers = {"X-API-Key": config.AGENCY_CRM_API_KEY}
    
    # Get system user (or create if doesn't exist)
    system_user = User.query.filter_by(username='system').first()
    if not system_user:
        system_user = User(
            username='system',
            email='system@internal.local',
            role='admin'
        )
        system_user.set_password('system123')
        db.session.add(system_user)
        db.session.commit()
        print("✓ Created system user")
    
    try:
        # Sync Companies
        print("Syncing companies...")
        response = requests.get(f"{base_url}/companies", headers=headers)
        if response.status_code == 200:
            companies = response.json()
            for company in companies:
                sync_company_to_advertiser(company, system_user.id)
            print(f"✓ Synced {len(companies)} companies")
        else:
            print(f"✗ Failed to get companies: {response.status_code}")
        
        # Sync Brands
        print("Syncing brands...")
        response = requests.get(f"{base_url}/brands", headers=headers)
        if response.status_code == 200:
            brands = response.json()
            for brand in brands:
                sync_brand_to_advertiser(brand, system_user.id)
            print(f"✓ Synced {len(brands)} brands")
        else:
            print(f"✗ Failed to get brands: {response.status_code}")
        
        # Sync Contacts
        print("Syncing contacts...")
        response = requests.get(f"{base_url}/contacts", headers=headers)
        if response.status_code == 200:
            contacts = response.json()
            for contact in contacts:
                sync_contact_from_crm(contact, system_user.id)
            print(f"✓ Synced {len(contacts)} contacts")
        else:
            print(f"✗ Failed to get contacts: {response.status_code}")
        
        # Sync Recent Invoices
        print("Syncing recent invoices...")
        response = requests.get(f"{base_url}/invoices", headers=headers)
        if response.status_code == 200:
            invoices = response.json()
            for invoice in invoices[:50]:  # Limit to 50 most recent
                create_invoice_activity_sync(invoice, system_user.id)
            print(f"✓ Synced {min(len(invoices), 50)} recent invoices")
        else:
            print(f"✗ Failed to get invoices: {response.status_code}")
        
        # Sync Recent Status Updates
        print("Syncing recent status updates...")
        response = requests.get(f"{base_url}/status-updates?limit=100", headers=headers)
        if response.status_code == 200:
            updates = response.json()
            for update in updates:
                create_status_activity_sync(update, system_user.id)
            print(f"✓ Synced {len(updates)} status updates")
        else:
            print(f"✗ Failed to get status updates: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error syncing from Agency CRM: {e}")

def sync_all_from_tv_planner():
    """Pull all existing data from TV Planner"""
    print("\n=== Syncing from TV Planner ===")
    
    base_url = config.TV_PLANNER_API_URL
    headers = {"X-API-Key": config.TV_PLANNER_API_KEY}
    
    system_user = User.query.filter_by(username='system').first()
    
    try:
        # Sync Campaigns
        print("Syncing campaigns...")
        response = requests.get(f"{base_url}/campaigns", headers=headers)
        if response.status_code == 200:
            campaigns = response.json()
            for campaign in campaigns:
                # Get spending data for each campaign
                spending_response = requests.get(
                    f"{base_url}/campaigns/{campaign['id']}/spending",
                    headers=headers
                )
                if spending_response.status_code == 200:
                    spending_data = spending_response.json()
                    campaign.update(spending_data)
                sync_campaign_spending_data(campaign, system_user.id)
            print(f"✓ Synced {len(campaigns)} campaigns")
        else:
            print(f"✗ Failed to get campaigns: {response.status_code}")
        
        # Sync Contacts from TV Planner
        print("Syncing TV planner contacts...")
        response = requests.get(f"{base_url}/contacts", headers=headers)
        if response.status_code == 200:
            contacts = response.json()
            for contact in contacts:
                sync_contact_from_tv(contact, system_user.id)
            print(f"✓ Synced {len(contacts)} TV planner contacts")
        else:
            print(f"✗ Failed to get TV contacts: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error syncing from TV Planner: {e}")

def sync_company_to_advertiser(company_data, user_id):
    """Sync company from agency-crm to advertiser"""
    advertiser = Advertiser.query.filter_by(name=company_data['name']).first()
    
    if not advertiser:
        advertiser = Advertiser(
            name=company_data['name'],
            current_agency='Our Agency',
            lead_status='ours',
            created_at=datetime.utcnow()
        )
        db.session.add(advertiser)
        db.session.flush()  # Get the ID
        
        # Add sync activity
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=user_id,
            activity_type='note',
            description=f"Initial sync: Company from Agency CRM (ID: {company_data.get('id')})",
            outcome='Data synchronized',
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
    else:
        # Update existing
        advertiser.lead_status = 'ours'

def sync_brand_to_advertiser(brand_data, user_id):
    """Sync brand from agency-crm to advertiser"""
    advertiser_name = f"{brand_data.get('company_name', 'Unknown')} - {brand_data['name']}"
    advertiser = Advertiser.query.filter_by(name=advertiser_name).first()
    
    if not advertiser:
        advertiser = Advertiser(
            name=advertiser_name,
            current_agency='Our Agency',
            lead_status='ours',
            created_at=datetime.utcnow()
        )
        db.session.add(advertiser)
        db.session.flush()
        
        # Add sync activity
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=user_id,
            activity_type='note',
            description=f"Initial sync: Brand from Agency CRM (Brand ID: {brand_data.get('id')})",
            outcome='Data synchronized',
            created_at=datetime.utcnow()
        )
        db.session.add(activity)

def sync_contact_from_crm(contact_data, user_id):
    """Sync contact from agency-crm"""
    if not contact_data.get('email'):
        return  # Skip contacts without email
    
    for brand in contact_data.get('brands', []):
        advertiser = Advertiser.query.filter(
            Advertiser.name.contains(brand['name'])
        ).first()
        
        if advertiser:
            existing_contact = Contact.query.filter_by(
                advertiser_id=advertiser.id,
                email=contact_data['email']
            ).first()
            
            if not existing_contact:
                contact = Contact(
                    advertiser_id=advertiser.id,
                    first_name=contact_data.get('first_name', ''),
                    last_name=contact_data.get('last_name', ''),
                    email=contact_data['email'],
                    phone=contact_data.get('phone'),
                    linkedin_url=contact_data.get('linkedin_url'),
                    added_by_id=user_id,
                    created_at=datetime.utcnow()
                )
                db.session.add(contact)

def sync_contact_from_tv(contact_data, user_id):
    """Sync contact from tv-planner"""
    if not contact_data.get('email'):
        return
    
    # Try to find a matching advertiser by company name
    advertiser = None
    if contact_data.get('company'):
        advertiser = Advertiser.query.filter(
            Advertiser.name.contains(contact_data['company'])
        ).first()
    
    # If no match found, create a generic advertiser
    if not advertiser:
        company_name = contact_data.get('company', 'TV Planner Contact')
        advertiser = Advertiser.query.filter_by(name=company_name).first()
        
        if not advertiser:
            advertiser = Advertiser(
                name=company_name,
                current_agency='Potential Client',
                lead_status='cold',
                created_at=datetime.utcnow()
            )
            db.session.add(advertiser)
            db.session.flush()
    
    # Add contact if not exists
    existing_contact = Contact.query.filter_by(
        advertiser_id=advertiser.id,
        email=contact_data['email']
    ).first()
    
    if not existing_contact:
        contact = Contact(
            advertiser_id=advertiser.id,
            first_name=contact_data.get('name', '').split(' ')[0] if contact_data.get('name') else '',
            last_name=' '.join(contact_data.get('name', '').split(' ')[1:]) if contact_data.get('name') else '',
            email=contact_data['email'],
            phone=contact_data.get('phone'),
            added_by_id=user_id,
            created_at=datetime.utcnow()
        )
        db.session.add(contact)

def create_invoice_activity_sync(invoice_data, user_id):
    """Create activity for invoice from sync"""
    advertiser = Advertiser.query.filter(
        Advertiser.name.contains(invoice_data.get('brand_name', ''))
    ).first()
    
    if advertiser:
        # Check if we already have this invoice activity
        existing = Activity.query.filter_by(
            advertiser_id=advertiser.id,
            activity_type='note'
        ).filter(
            Activity.description.contains(f"Invoice: {invoice_data.get('invoice_date')}")
        ).first()
        
        if not existing:
            activity = Activity(
                advertiser_id=advertiser.id,
                user_id=user_id,
                activity_type='note',
                description=f"Invoice: {invoice_data.get('invoice_date')} - "
                           f"Amount: {invoice_data.get('total_amount')} EUR",
                outcome='Invoice from Agency CRM',
                created_at=datetime.utcnow()
            )
            db.session.add(activity)

def create_status_activity_sync(update_data, user_id):
    """Create activity for status update from sync"""
    advertiser = Advertiser.query.filter(
        Advertiser.name.contains(update_data.get('brand_name', ''))
    ).first()
    
    if advertiser:
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=user_id,
            activity_type='note',
            description=f"Status Update: {update_data.get('update_text', '')}",
            outcome=f"By: {update_data.get('created_by', 'Unknown')}",
            created_at=datetime.utcnow()
        )
        db.session.add(activity)

def sync_campaign_spending_data(campaign_data, user_id):
    """Sync campaign spending from tv-planner"""
    # Try to match campaign name to advertiser
    campaign_name = campaign_data.get('name', '')
    advertiser_name = campaign_name.split('-')[0].strip() if campaign_name else ''
    
    if not advertiser_name:
        return
    
    advertiser = Advertiser.query.filter(
        Advertiser.name.contains(advertiser_name)
    ).first()
    
    if not advertiser:
        # Create new advertiser from campaign
        advertiser = Advertiser(
            name=advertiser_name,
            current_agency='TV Planner Client',
            lead_status='warm',
            created_at=datetime.utcnow()
        )
        db.session.add(advertiser)
        db.session.flush()
    
    # Update spending data
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
    
    # Update TV spending
    total_spending = campaign_data.get('total_spending', 0)
    if total_spending > 0:
        spending.tv = max(spending.tv or 0, total_spending)
    
    # Add activity
    activity = Activity(
        advertiser_id=advertiser.id,
        user_id=user_id,
        activity_type='note',
        description=f"Initial sync: TV Campaign '{campaign_name}'",
        outcome=f"Spending: {total_spending} EUR" if total_spending else "Campaign data synchronized",
        created_at=datetime.utcnow()
    )
    db.session.add(activity)

def main():
    print("=" * 60)
    print("NewBusiness Initial Data Sync")
    print("=" * 60)
    print("\nThis will pull ALL existing data from Agency CRM and TV Planner")
    print("and populate NewBusiness with current information.")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print(f"\nConnecting to NewBusiness database...")
        
        # Sync all data
        sync_all_from_agency_crm()
        sync_all_from_tv_planner()
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n✓ All data committed to database")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error committing data: {e}")
            return
    
    print("\n" + "=" * 60)
    print("Initial Sync Complete!")
    print("=" * 60)
    print("\nNewBusiness now contains:")
    print("- All companies and brands from Agency CRM")
    print("- All contacts with advertiser relationships") 
    print("- Recent invoices as activity logs")
    print("- Recent status updates as activities")
    print("- All TV campaigns with spending data")
    print("- TV planner contacts")
    print("\nFuture updates will be handled automatically via webhooks!")

if __name__ == '__main__':
    main()