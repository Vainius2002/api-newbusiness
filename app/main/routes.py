from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db
from app.main import bp
from app.models import Advertiser, User, Activity, LeadStatusHistory, SpendingData
from app.utils import process_csv_upload
from sqlalchemy import func, desc, case

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # Get pagination parameters
    leads_page = request.args.get('leads_page', 1, type=int)
    activities_page = request.args.get('activities_page', 1, type=int)
    
    # Get dashboard statistics
    total_advertisers = Advertiser.query.count()
    
    # Lead status counts
    lead_status_counts = db.session.query(
        Advertiser.lead_status, 
        func.count(Advertiser.id)
    ).group_by(Advertiser.lead_status).all()
    
    # Recent activities with pagination
    recent_activities_query = Activity.query.order_by(
        Activity.created_at.desc()
    )
    recent_activities = recent_activities_query.paginate(
        page=activities_page, per_page=50, error_out=False
    )
    
    # Get leads needing attention (hot, warm, cold) with their last activity date
    # Subquery to get last activity date for each advertiser
    last_activity_subq = db.session.query(
        Activity.advertiser_id,
        func.max(Activity.created_at).label('last_activity_date')
    ).group_by(Activity.advertiser_id).subquery()
    
    # Get hot, warm, and cold leads with their details
    leads_query = db.session.query(
        Advertiser,
        last_activity_subq.c.last_activity_date
    ).outerjoin(
        last_activity_subq,
        Advertiser.id == last_activity_subq.c.advertiser_id
    ).filter(
        Advertiser.lead_status.in_(['hot', 'warm', 'cold', 'get_info'])
    ).order_by(
        # Sort by oldest activity first (nulls first)
        func.coalesce(last_activity_subq.c.last_activity_date, func.datetime('1900-01-01')).asc()
    )
    
    # Paginate the leads
    leads_paginated = leads_query.paginate(
        page=leads_page, per_page=50, error_out=False
    )
    
    # Calculate days ago for each lead
    leads_with_days_ago = []
    today = datetime.utcnow()
    for advertiser, last_activity_date in leads_paginated.items:
        if last_activity_date:
            days_ago = (today - last_activity_date).days
            days_ago_str = f"{days_ago} days ago" if days_ago != 1 else "1 day ago"
            if days_ago == 0:
                days_ago_str = "Today"
        else:
            days_ago_str = "Never"
            days_ago = float('inf')  # For sorting purposes
        
        leads_with_days_ago.append({
            'advertiser': advertiser,
            'last_activity': days_ago_str,
            'days_ago_num': days_ago
        })
    
    return render_template('main/index.html',
                         total_advertisers=total_advertisers,
                         lead_status_counts=dict(lead_status_counts),
                         recent_activities=recent_activities,
                         leads_needing_attention=leads_with_days_ago,
                         leads_pagination=leads_paginated)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if not current_user.is_admin():
        flash('Only administrators can upload data.', 'warning')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            success, message = process_csv_upload(filepath)
            
            # Delete the uploaded file after processing
            os.remove(filepath)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            
            return redirect(url_for('main.index'))
        else:
            flash('Please upload a CSV file', 'danger')
    
    return render_template('main/upload.html')