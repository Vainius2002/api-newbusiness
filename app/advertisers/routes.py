from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.advertisers import bp
from app.advertisers.forms import AdvertiserForm, LeadStatusForm, BulkAssignForm, SpendingDataForm
from app.models import Advertiser, SpendingData, Activity, LeadStatusHistory, User, Contact, Attachment
from app.utils import get_lead_status_color
from sqlalchemy import func, or_

@bp.route('/')
@login_required
def list_advertisers():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    agency_filter = request.args.get('agency', '')
    assigned_filter = request.args.get('assigned', '')
    sort = request.args.get('sort', 'net')  # Default to net spending
    order = request.args.get('order', 'desc')
    
    # Base query with spending data aggregation
    # Subquery to get latest year spending for each advertiser
    latest_year_subq = db.session.query(
        SpendingData.advertiser_id,
        func.max(SpendingData.year).label('latest_year')
    ).group_by(SpendingData.advertiser_id).subquery()
    
    # Subquery to get spending data for latest year
    latest_spending_subq = db.session.query(
        SpendingData.advertiser_id,
        SpendingData.grand_total.label('gross_spending'),
        func.coalesce(SpendingData.net_total, 
            SpendingData.tv * 0.2 + 
            SpendingData.cinema * 0.2 + 
            SpendingData.radio * 0.3 + 
            SpendingData.outdoor_static * 0.5 + 
            SpendingData.billboard * 0.5 + 
            SpendingData.internet * 0.5 + 
            SpendingData.magazines * 0.5 + 
            SpendingData.newspapers * 0.5 + 
            SpendingData.indoor_tv * 0.5
        ).label('net_spending')
    ).join(
        latest_year_subq,
        (SpendingData.advertiser_id == latest_year_subq.c.advertiser_id) & 
        (SpendingData.year == latest_year_subq.c.latest_year)
    ).subquery()
    
    # Main query
    query = db.session.query(
        Advertiser,
        func.coalesce(latest_spending_subq.c.gross_spending, 0).label('last_year_gross'),
        func.coalesce(latest_spending_subq.c.net_spending, 0).label('last_year_net')
    ).outerjoin(
        latest_spending_subq,
        Advertiser.id == latest_spending_subq.c.advertiser_id
    )
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Advertiser.name.ilike(f'%{search}%'),
                Advertiser.current_agency.ilike(f'%{search}%')
            )
        )
    
    if status_filter:
        query = query.filter(Advertiser.lead_status == status_filter)
    
    if agency_filter:
        query = query.filter(Advertiser.current_agency == agency_filter)
    
    if assigned_filter:
        if assigned_filter == 'unassigned':
            query = query.filter(Advertiser.assigned_user_id.is_(None))
        else:
            query = query.filter(Advertiser.assigned_user_id == int(assigned_filter))
    
    # Apply role-based filtering
    if not current_user.is_team_lead():
        query = query.filter(Advertiser.assigned_user_id == current_user.id)
    
    # Apply sorting
    if sort == 'gross':
        if order == 'asc':
            query = query.order_by('last_year_gross')
        else:
            query = query.order_by(db.desc('last_year_gross'))
    elif sort == 'net':
        if order == 'asc':
            query = query.order_by('last_year_net')
        else:
            query = query.order_by(db.desc('last_year_net'))
    else:
        query = query.order_by(Advertiser.name)
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=100, error_out=False)
    
    # Process results to create advertiser data with spending
    advertisers = []
    for advertiser, gross, net in pagination.items:
        # Create a dictionary-like object to hold advertiser and spending data
        advertiser_data = {
            'advertiser': advertiser,
            'last_year_gross_spending': gross,
            'last_year_net_spending': net
        }
        advertisers.append(advertiser_data)
    
    # Get unique agencies for filter dropdown
    agencies = db.session.query(Advertiser.current_agency).distinct().filter(
        Advertiser.current_agency.isnot(None)
    ).order_by(Advertiser.current_agency).all()
    agencies = [a[0] for a in agencies if a[0]]
    
    # Get users for assigned filter
    if current_user.is_team_lead():
        users = User.query.order_by(User.username).all()
    else:
        users = [current_user]
    
    bulk_assign_form = BulkAssignForm() if current_user.is_team_lead() else None
    
    return render_template('advertisers/list.html',
                         advertisers=advertisers,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         agency_filter=agency_filter,
                         assigned_filter=assigned_filter,
                         agencies=agencies,
                         users=users,
                         bulk_assign_form=bulk_assign_form,
                         sort=sort,
                         order=order,
                         get_lead_status_color=get_lead_status_color)

@bp.route('/<int:id>')
@login_required
def view_advertiser(id):
    advertiser = Advertiser.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to view this advertiser.', 'warning')
        return redirect(url_for('advertisers.list_advertisers'))
    
    # Get spending data by year
    spending_data = SpendingData.query.filter_by(
        advertiser_id=id
    ).order_by(SpendingData.year.desc()).all()
    
    # Get recent activities
    activities = Activity.query.filter_by(
        advertiser_id=id
    ).order_by(Activity.created_at.desc()).limit(20).all()
    
    # Get status history
    status_history = LeadStatusHistory.query.filter_by(
        advertiser_id=id
    ).order_by(LeadStatusHistory.changed_at.desc()).all()
    
    # Get contacts
    contacts = advertiser.contacts.order_by('last_name', 'first_name').all()
    
    # Get attachments
    attachments = advertiser.attachments.order_by(Attachment.uploaded_at.desc()).all()
    
    return render_template('advertisers/view.html',
                         advertiser=advertiser,
                         spending_data=spending_data,
                         activities=activities,
                         status_history=status_history,
                         contacts=contacts,
                         attachments=attachments,
                         get_lead_status_color=get_lead_status_color)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_advertiser():
    if not current_user.is_team_lead():
        flash('Only team leads and admins can create advertisers.', 'warning')
        return redirect(url_for('advertisers.list_advertisers'))
    
    form = AdvertiserForm()
    if form.validate_on_submit():
        advertiser = Advertiser(
            name=form.name.data,
            current_agency=form.current_agency.data,
            lead_status=form.lead_status.data,
            assigned_user_id=form.assigned_user_id.data if form.assigned_user_id.data != 0 else None
        )
        db.session.add(advertiser)
        db.session.commit()
        flash('Advertiser created successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    return render_template('advertisers/form.html', form=form, title='Create Advertiser')

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_advertiser(id):
    advertiser = Advertiser.query.get_or_404(id)
    
    if not current_user.is_team_lead():
        flash('Only team leads and admins can edit advertisers.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=id))
    
    form = AdvertiserForm(obj=advertiser)
    if form.validate_on_submit():
        advertiser.name = form.name.data
        advertiser.current_agency = form.current_agency.data
        advertiser.lead_status = form.lead_status.data
        advertiser.assigned_user_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None
        db.session.commit()
        flash('Advertiser updated successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    return render_template('advertisers/form.html', form=form, title='Edit Advertiser')

@bp.route('/<int:id>/update_status', methods=['GET', 'POST'])
@login_required
def update_status(id):
    advertiser = Advertiser.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to update this advertiser.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=id))
    
    form = LeadStatusForm()
    if form.validate_on_submit():
        # Create status history record
        history = LeadStatusHistory(
            advertiser_id=advertiser.id,
            user_id=current_user.id,
            old_status=advertiser.lead_status,
            new_status=form.new_status.data,
            reason=form.reason.data
        )
        db.session.add(history)
        
        # Update advertiser status
        advertiser.lead_status = form.new_status.data
        db.session.commit()
        
        flash('Lead status updated successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    return render_template('advertisers/update_status.html', 
                         form=form, 
                         advertiser=advertiser,
                         get_lead_status_color=get_lead_status_color)

@bp.route('/bulk_assign', methods=['POST'])
@login_required
def bulk_assign():
    if not current_user.is_team_lead():
        return jsonify({'error': 'Permission denied'}), 403
    
    advertiser_ids = request.form.getlist('advertiser_ids[]')
    user_id = request.form.get('user_id')
    
    if not advertiser_ids or not user_id:
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        advertisers = Advertiser.query.filter(
            Advertiser.id.in_(advertiser_ids)
        ).all()
        
        for advertiser in advertisers:
            advertiser.assigned_user_id = int(user_id)
        
        db.session.commit()
        return jsonify({'success': True, 'count': len(advertisers)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>/spending/add', methods=['GET', 'POST'])
@login_required
def add_spending(id):
    if not current_user.is_team_lead():
        flash('You do not have permission to add spending data.', 'danger')
        return redirect(url_for('advertisers.view_advertiser', id=id))
    
    advertiser = Advertiser.query.get_or_404(id)
    form = SpendingDataForm()
    
    if form.validate_on_submit():
        # Check if spending data already exists for this year
        existing = SpendingData.query.filter_by(
            advertiser_id=advertiser.id,
            year=form.year.data
        ).first()
        
        if existing:
            flash(f'Spending data for {form.year.data} already exists. Please edit instead.', 'warning')
            return redirect(url_for('advertisers.edit_spending', id=id, year=form.year.data))
        
        spending = SpendingData(
            advertiser_id=advertiser.id,
            year=form.year.data,
            cinema=form.cinema.data or 0,
            billboard=form.billboard.data or 0,
            indoor_tv=form.indoor_tv.data or 0,
            internet=form.internet.data or 0,
            magazines=form.magazines.data or 0,
            newspapers=form.newspapers.data or 0,
            outdoor_static=form.outdoor_static.data or 0,
            radio=form.radio.data or 0,
            tv=form.tv.data or 0,
            grand_total=form.grand_total.data or 0,
            net_total=form.net_total.data if form.net_total.data else None
        )
        
        db.session.add(spending)
        db.session.commit()
        
        flash('Spending data added successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    return render_template('advertisers/spending_form.html', 
                         form=form, 
                         advertiser=advertiser,
                         action='Add')

@bp.route('/<int:id>/spending/<int:year>/edit', methods=['GET', 'POST'])
@login_required
def edit_spending(id, year):
    if not current_user.is_team_lead():
        flash('You do not have permission to edit spending data.', 'danger')
        return redirect(url_for('advertisers.view_advertiser', id=id))
    
    advertiser = Advertiser.query.get_or_404(id)
    spending = SpendingData.query.filter_by(
        advertiser_id=advertiser.id,
        year=year
    ).first_or_404()
    
    form = SpendingDataForm(obj=spending)
    
    if form.validate_on_submit():
        spending.cinema = form.cinema.data or 0
        spending.billboard = form.billboard.data or 0
        spending.indoor_tv = form.indoor_tv.data or 0
        spending.internet = form.internet.data or 0
        spending.magazines = form.magazines.data or 0
        spending.newspapers = form.newspapers.data or 0
        spending.outdoor_static = form.outdoor_static.data or 0
        spending.radio = form.radio.data or 0
        spending.tv = form.tv.data or 0
        spending.grand_total = form.grand_total.data or 0
        spending.net_total = form.net_total.data if form.net_total.data else None
        
        db.session.commit()
        
        flash('Spending data updated successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser.id))
    
    return render_template('advertisers/spending_form.html', 
                         form=form, 
                         advertiser=advertiser,
                         action='Edit')

@bp.route('/api/advertisers/<int:id>/contacts')
@login_required
def api_get_advertiser_contacts(id):
    """API endpoint to get contacts for an advertiser."""
    advertiser = Advertiser.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    contacts = Contact.query.filter_by(advertiser_id=id).order_by(Contact.last_name, Contact.first_name).all()
    
    return jsonify({
        'contacts': [
            {
                'id': contact.id,
                'full_name': contact.full_name
            }
            for contact in contacts
        ]
    })