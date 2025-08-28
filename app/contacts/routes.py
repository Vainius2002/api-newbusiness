from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.contacts import bp
from app.contacts.forms import ContactForm
from app.models import Contact, Advertiser
from sqlalchemy import or_
from datetime import datetime

@bp.route('/')
@login_required
def list_contacts():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    advertiser_id = request.args.get('advertiser', type=int)
    
    # Base query - use LEFT JOIN to include contacts without advertisers
    query = Contact.query.outerjoin(Advertiser)
    
    # Filter by user permissions
    if not current_user.is_team_lead():
        query = query.filter(
            or_(
                Advertiser.assigned_user_id == current_user.id,
                Contact.advertiser_id.is_(None)  # Include contacts without advertisers
            )
        )
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Contact.first_name.contains(search),
                Contact.last_name.contains(search),
                Contact.email.contains(search),
                Advertiser.name.contains(search)
            )
        )
    
    # Filter by advertiser
    if advertiser_id:
        query = query.filter(Contact.advertiser_id == advertiser_id)
    
    # Get advertisers for filter dropdown
    if current_user.is_team_lead():
        advertisers = Advertiser.query.order_by(Advertiser.name).all()
    else:
        advertisers = Advertiser.query.filter_by(
            assigned_user_id=current_user.id
        ).order_by(Advertiser.name).all()
    
    # Paginate results
    contacts = query.order_by(Contact.last_name, Contact.first_name).paginate(
        page=page, per_page=100, error_out=False
    )
    
    return render_template('contacts/list.html',
                         contacts=contacts,
                         search=search,
                         advertisers=advertisers,
                         advertiser_id=advertiser_id)

@bp.route('/add/<int:advertiser_id>', methods=['GET', 'POST'])
@login_required
def add_contact(advertiser_id):
    from app.models import Activity
    
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to add contacts for this advertiser.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser_id))
    
    form = ContactForm()
    
    # Pre-select the current advertiser
    if request.method == 'GET':
        form.advertisers.data = [advertiser_id]
    
    if form.validate_on_submit():
        selected_advertiser_ids = form.advertisers.data or []
        
        if not selected_advertiser_ids:
            flash('Please select at least one advertiser.', 'error')
            return render_template('contacts/form.html', form=form, advertiser=advertiser, action='Add')
        
        # Create contact with first selected advertiser as primary
        contact = Contact(
            advertiser_id=selected_advertiser_ids[0],
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            linkedin_url=form.linkedin_url.data,
            added_by_id=current_user.id
        )
        db.session.add(contact)
        db.session.flush()  # Get contact ID
        
        # Create relationship activities for other selected advertisers
        for advertiser_id_sel in selected_advertiser_ids:
            if advertiser_id_sel != contact.advertiser_id:
                activity = Activity(
                    advertiser_id=advertiser_id_sel,
                    user_id=current_user.id,
                    activity_type='note',
                    description=f"Contact relationship established: {contact.first_name} {contact.last_name}",
                    outcome=f"Contact: {contact.email} | Phone: {contact.phone or 'N/A'}",
                    created_at=datetime.utcnow()
                )
                db.session.add(activity)
        
        db.session.commit()
        flash('Contact added successfully!', 'success')
        return redirect(url_for('contacts.list_contacts'))
    
    return render_template('contacts/form.html',
                         form=form,
                         advertiser=advertiser,
                         action='Add')

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(id):
    from app.models import Activity
    
    contact = Contact.query.get_or_404(id)
    primary_advertiser = contact.advertiser
    
    # Check permissions - can edit if user has access to any related advertiser or contact has no advertiser
    if not current_user.is_team_lead():
        related_advertisers = contact.get_related_advertisers()
        if related_advertisers:
            user_has_access = any(adv.assigned_user_id == current_user.id for adv in related_advertisers)
            if not user_has_access:
                flash('You do not have permission to edit this contact.', 'warning')
                if primary_advertiser:
                    return redirect(url_for('advertisers.view_advertiser', id=primary_advertiser.id))
                else:
                    return redirect(url_for('contacts.list_contacts'))
        # If contact has no related advertisers, allow any user to edit it
    
    form = ContactForm(obj=contact)
    
    # Pre-populate current advertiser relationships
    if request.method == 'GET':
        related_advertisers = contact.get_related_advertisers() 
        form.advertisers.data = [adv.id for adv in related_advertisers]
    
    if form.validate_on_submit():
        # Update contact information
        contact.first_name = form.first_name.data
        contact.last_name = form.last_name.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        contact.linkedin_url = form.linkedin_url.data
        
        # Handle advertiser relationships
        selected_advertiser_ids = form.advertisers.data or []
        
        # Always clear old relationship activities for this contact
        old_activities = Activity.query.filter(
            Activity.description.contains(f"Contact relationship established: {contact.first_name} {contact.last_name}")
        ).all()
        for activity in old_activities:
            db.session.delete(activity)
        
        if selected_advertiser_ids:
            # Set first selected advertiser as primary
            contact.advertiser_id = selected_advertiser_ids[0]
            
            # Create activities for all selected advertisers except the primary one
            for advertiser_id in selected_advertiser_ids:
                if advertiser_id != contact.advertiser_id:
                    # Create relationship activity for non-primary advertisers
                    activity = Activity(
                        advertiser_id=advertiser_id,
                        user_id=current_user.id,
                        activity_type='note',
                        description=f"Contact relationship established: {contact.first_name} {contact.last_name}",
                        outcome=f"Contact: {contact.email} | Phone: {contact.phone or 'N/A'}",
                        created_at=datetime.utcnow()
                    )
                    db.session.add(activity)
        else:
            # No advertisers selected - set primary advertiser to None
            contact.advertiser_id = None
        
        db.session.commit()
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('contacts.list_contacts'))
    
    return render_template('contacts/form.html',
                         form=form,
                         advertiser=primary_advertiser,
                         contact=contact,
                         action='Edit')

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    advertiser = contact.advertiser
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to delete this contact.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    db.session.delete(contact)
    db.session.commit()
    
    flash('Contact deleted successfully!', 'success')
    if advertiser:
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    else:
        return redirect(url_for('contacts.list_contacts'))