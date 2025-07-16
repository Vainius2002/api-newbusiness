from flask import render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db
from app.activities import bp
from app.activities.forms import ActivityForm
from app.models import Activity, Advertiser, Attachment

@bp.route('/add/<int:advertiser_id>', methods=['GET', 'POST'])
@login_required
def add_activity(advertiser_id):
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to add activities for this advertiser.', 'warning')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser_id))
    
    form = ActivityForm(advertiser_id=advertiser_id)
    if form.validate_on_submit():
        activity = Activity(
            advertiser_id=advertiser.id,
            user_id=current_user.id,
            contact_id=form.contact_id.data if form.contact_id.data != 0 else None,
            activity_type=form.activity_type.data,
            description=form.description.data,
            outcome=form.outcome.data
        )
        db.session.add(activity)
        
        # Handle file attachment if provided
        if form.attachment.data:
            file = form.attachment.data
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            attachment = Attachment(
                advertiser_id=advertiser.id,
                filename=file.filename,
                file_path=filepath,
                uploaded_by_id=current_user.id
            )
            db.session.add(attachment)
        
        db.session.commit()
        flash('Activity logged successfully!', 'success')
        return redirect(url_for('advertisers.view_advertiser', id=advertiser_id))
    
    return render_template('activities/form.html', 
                         form=form, 
                         advertiser=advertiser)

@bp.route('/feed')
@login_required
def activity_feed():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query
    query = Activity.query
    
    # Filter by user if not team lead
    if not current_user.is_team_lead():
        query = query.join(Advertiser).filter(
            Advertiser.assigned_user_id == current_user.id
        )
    
    # Paginate results
    activities = query.order_by(
        Activity.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all advertisers for the modal form
    if current_user.is_team_lead():
        all_advertisers = Advertiser.query.order_by(Advertiser.name).all()
    else:
        all_advertisers = Advertiser.query.filter_by(
            assigned_user_id=current_user.id
        ).order_by(Advertiser.name).all()
    
    return render_template('activities/feed.html', 
                         activities=activities,
                         all_advertisers=all_advertisers)

@bp.route('/download/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    advertiser = attachment.advertiser
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to download this file.', 'warning')
        return redirect(url_for('main.index'))
    
    return send_file(attachment.file_path, 
                    download_name=attachment.filename,
                    as_attachment=True)

@bp.route('/create_modal', methods=['POST'])
@login_required
def create_activity_modal():
    """Handle activity creation from modal form."""
    advertiser_id = request.form.get('advertiser_id', type=int)
    contact_id = request.form.get('contact_id', type=int)
    activity_type = request.form.get('activity_type')
    description = request.form.get('description')
    outcome = request.form.get('outcome')
    
    if not advertiser_id or not activity_type or not description:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('activities.activity_feed'))
    
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    
    # Check permissions
    if not current_user.is_team_lead() and advertiser.assigned_user_id != current_user.id:
        flash('You do not have permission to add activities for this advertiser.', 'warning')
        return redirect(url_for('activities.activity_feed'))
    
    activity = Activity(
        advertiser_id=advertiser.id,
        user_id=current_user.id,
        contact_id=contact_id if contact_id and contact_id != 0 else None,
        activity_type=activity_type,
        description=description,
        outcome=outcome if outcome else None
    )
    db.session.add(activity)
    db.session.commit()
    
    flash('Activity logged successfully!', 'success')
    return redirect(url_for('activities.activity_feed'))