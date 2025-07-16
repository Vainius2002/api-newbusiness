from flask import render_template, request, make_response
from flask_login import login_required, current_user
import plotly.graph_objs as go
import plotly.utils
import json
import pandas as pd
from io import BytesIO
from app import db
from app.reports import bp
from app.models import Advertiser, SpendingData, Activity, User, LeadStatusHistory
from sqlalchemy import func, desc
from datetime import datetime, timedelta

@bp.route('/dashboard')
@login_required
def dashboard():
    # Lead pipeline data
    lead_pipeline = db.session.query(
        Advertiser.lead_status,
        func.count(Advertiser.id).label('count')
    ).group_by(Advertiser.lead_status).all()
    
    # Create pipeline chart
    statuses = [item[0] for item in lead_pipeline]
    counts = [item[1] for item in lead_pipeline]
    
    pipeline_chart = go.Figure(data=[
        go.Bar(
            x=statuses,
            y=counts,
            marker_color=['#007bff', '#ffc107', '#dc3545', '#6c757d']
        )
    ])
    pipeline_chart.update_layout(
        title='Lead Pipeline Status',
        xaxis_title='Status',
        yaxis_title='Count',
        showlegend=False
    )
    
    # Team performance data
    if current_user.is_team_lead():
        team_performance = db.session.query(
            User.username,
            func.count(Activity.id).label('activity_count')
        ).join(Activity).group_by(User.id).order_by(desc('activity_count')).limit(10).all()
    else:
        team_performance = []
    
    # Spending trends by year
    spending_trends = db.session.query(
        SpendingData.year,
        func.sum(SpendingData.grand_total).label('total')
    ).group_by(SpendingData.year).order_by(SpendingData.year).all()
    
    if spending_trends:
        years = [str(item[0]) for item in spending_trends]
        totals = [item[1] for item in spending_trends]
        
        spending_chart = go.Figure(data=[
            go.Scatter(
                x=years,
                y=totals,
                mode='lines+markers',
                name='Total Spending',
                line=dict(color='#007bff', width=3)
            )
        ])
        spending_chart.update_layout(
            title='Total Advertiser Spending by Year',
            xaxis_title='Year',
            yaxis_title='Spending (€)',
            showlegend=False
        )
    else:
        spending_chart = None
    
    # Convert charts to JSON
    pipeline_json = json.dumps(pipeline_chart, cls=plotly.utils.PlotlyJSONEncoder)
    spending_json = json.dumps(spending_chart, cls=plotly.utils.PlotlyJSONEncoder) if spending_chart else None
    
    return render_template('reports/dashboard.html',
                         pipeline_json=pipeline_json,
                         spending_json=spending_json,
                         team_performance=team_performance)

@bp.route('/export')
@login_required
def export_data():
    if not current_user.is_team_lead():
        flash('Only team leads and admins can export data.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get filter parameters
    format_type = request.args.get('format', 'csv')
    report_type = request.args.get('type', 'advertisers')
    
    if report_type == 'advertisers':
        # Export advertisers with spending data
        advertisers = db.session.query(
            Advertiser.name,
            Advertiser.current_agency,
            Advertiser.lead_status,
            User.username.label('assigned_to'),
            func.sum(SpendingData.grand_total).label('total_spending')
        ).outerjoin(User, Advertiser.assigned_user_id == User.id
        ).outerjoin(SpendingData
        ).group_by(Advertiser.id).all()
        
        df = pd.DataFrame(advertisers)
        
    elif report_type == 'activities':
        # Export recent activities
        activities = db.session.query(
            Activity.created_at,
            User.username,
            Advertiser.name.label('advertiser'),
            Activity.activity_type,
            Activity.description,
            Activity.outcome
        ).join(User).join(Advertiser).order_by(
            Activity.created_at.desc()
        ).limit(1000).all()
        
        df = pd.DataFrame(activities)
    
    # Generate file
    output = BytesIO()
    if format_type == 'csv':
        df.to_csv(output, index=False)
        mimetype = 'text/csv'
        filename = f'{report_type}_export_{datetime.now().strftime("%Y%m%d")}.csv'
    else:  # Excel
        df.to_excel(output, index=False)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'{report_type}_export_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = mimetype
    
    return response

@bp.route('/spending_analysis')
@login_required
def spending_analysis():
    # Get top advertisers by channel
    channels = ['cinema', 'billboard', 'indoor_tv', 'internet', 'magazines', 
                'newspapers', 'outdoor_static', 'radio', 'tv']
    
    channel_data = {}
    for channel in channels:
        query = db.session.query(
            Advertiser.name,
            func.sum(getattr(SpendingData, channel)).label('total')
        ).join(SpendingData).group_by(
            Advertiser.id
        ).order_by(desc('total')).limit(5).all()
        
        channel_data[channel] = query
    
    # Create channel comparison chart
    channel_totals = []
    for channel in channels:
        total = db.session.query(
            func.sum(getattr(SpendingData, channel))
        ).scalar() or 0
        channel_totals.append((channel.replace('_', ' ').title(), total))
    
    channel_totals.sort(key=lambda x: x[1], reverse=True)
    
    channel_chart = go.Figure(data=[
        go.Bar(
            x=[item[0] for item in channel_totals],
            y=[item[1] for item in channel_totals],
            marker_color='#007bff'
        )
    ])
    channel_chart.update_layout(
        title='Total Spending by Media Channel',
        xaxis_title='Channel',
        yaxis_title='Total Spending (€)',
        xaxis_tickangle=-45
    )
    
    channel_json = json.dumps(channel_chart, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('reports/spending_analysis.html',
                         channel_data=channel_data,
                         channel_json=channel_json)