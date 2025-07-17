from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.contacts import bp
from app.contacts.forms import ContactForm
from app.models import Contact, Advertiser
from sqlalchemy import or_

@bp.route('/')
@login_required
def list_contacts():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    advertiser_id = request.args.get('advertiser', type=int)
    
    # Base query
    query = Contact.query.join(Advertiser)
    
    # Filter by user permissions
    if not current_user.is_team_lead():
        query = query.filter(Advertiser.assigned_user_id == current_user.id)
    
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
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to add contacts for this advertiser.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser_id))
    
    form = ContactForm()
    if form.validate_on_submit():
        contact = Contact(
            advertiser_id=advertiser.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            linkedin_url=form.linkedin_url.data,
            added_by_id=current_user.id
        )
        db.session.add(contact)
        db.session.commit()
        
        flash('Contact added successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser_id))
    
    return render_template('contacts/form.html',
                         form=form,
                         advertiser=advertiser,
                         action='Add')

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    advertiser = contact.advertiser
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to edit this contact.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    form = ContactForm(obj=contact)
    
    # Populate advertiser choices
    if current_user.is_team_lead():
        advertisers = Advertiser.query.order_by(Advertiser.name).all()
    else:
        advertisers = Advertiser.query.filter_by(
            assigned_user_id=current_user.id
        ).order_by(Advertiser.name).all()
    
    form.advertiser_id.choices = [(a.id, a.name) for a in advertisers]
    
    if form.validate_on_submit():
        contact.first_name = form.first_name.data
        contact.last_name = form.last_name.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        contact.linkedin_url = form.linkedin_url.data
        contact.advertiser_id = form.advertiser_id.data
        db.session.commit()
        
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=contact.advertiser_id))
    
    return render_template('contacts/form.html',
                         form=form,
                         advertiser=advertiser,
                         contact=contact,
                         action='Edit')

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    advertiser = contact.advertiser
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to delete this contact.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    db.session.delete(contact)
    db.session.commit()
    
    flash('Contact deleted successfully!', 'success')
    return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))