from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.main import bp
from app.models import Advertiser, User, Activity, LeadStatusHistory, SpendingData
from app.utils import process_csv_upload
from sqlalchemy import func, desc

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # Get dashboard statistics
    total_advertisers = Advertiser.query.count()
    
    # Lead status counts
    lead_status_counts = db.session.query(
        Advertiser.lead_status, 
        func.count(Advertiser.id)
    ).group_by(Advertiser.lead_status).all()
    
    # Recent activities
    recent_activities = Activity.query.order_by(
        Activity.created_at.desc()
    ).limit(10).all()
    
    # Top spenders
    top_spenders = db.session.query(
        Advertiser.name,
        func.sum(SpendingData.grand_total).label('total_spend')
    ).join(SpendingData).group_by(
        Advertiser.id
    ).order_by(desc('total_spend')).limit(10).all()
    
    return render_template('main/index.html',
                         total_advertisers=total_advertisers,
                         lead_status_counts=dict(lead_status_counts),
                         recent_activities=recent_activities,
                         top_spenders=top_spenders)

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