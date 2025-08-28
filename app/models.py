from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default='account_executive')  # admin, team_lead, account_executive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assigned_advertisers = db.relationship('Advertiser', backref='assigned_user', lazy='dynamic')
    activities = db.relationship('Activity', backref='user', lazy='dynamic')
    lead_status_changes = db.relationship('LeadStatusHistory', backref='changed_by_user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_team_lead(self):
        return self.role in ['admin', 'team_lead']

class Advertiser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    current_agency = db.Column(db.String(200))
    lead_status = db.Column(db.String(20), default='non_qualified')  # non_qualified, ours, cold, warm, hot, lost, non_market, get_info, network
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    spending_data = db.relationship('SpendingData', backref='advertiser', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='advertiser', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('LeadStatusHistory', backref='advertiser', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='advertiser', lazy='dynamic', cascade='all, delete-orphan')
    contacts = db.relationship('Contact', backref='advertiser', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def latest_spending_data(self):
        """Get the most recent year's spending data."""
        return self.spending_data.order_by(SpendingData.year.desc()).first()
    
    @property
    def last_year_gross_spending(self):
        """Get gross spending for the most recent year."""
        latest = self.latest_spending_data
        return latest.grand_total if latest else 0
    
    @property
    def last_year_net_spending(self):
        """Get net spending for the most recent year."""
        latest = self.latest_spending_data
        return latest.calculated_net_total if latest else 0

class SpendingData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    cinema = db.Column(db.Float, default=0)
    billboard = db.Column(db.Float, default=0)
    indoor_tv = db.Column(db.Float, default=0)
    internet = db.Column(db.Float, default=0)
    magazines = db.Column(db.Float, default=0)
    newspapers = db.Column(db.Float, default=0)
    outdoor_static = db.Column(db.Float, default=0)
    radio = db.Column(db.Float, default=0)
    tv = db.Column(db.Float, default=0)
    grand_total = db.Column(db.Float, default=0)
    net_total = db.Column(db.Float, nullable=True)  # Manually entered net spending
    
    __table_args__ = (db.UniqueConstraint('advertiser_id', 'year', name='_advertiser_year_uc'),)
    
    @property
    def calculated_net_total(self):
        """Calculate net total if not manually set, using industry discounts."""
        if self.net_total is not None:
            return self.net_total
        
        # Apply standard industry discounts
        net = 0
        net += self.tv * 0.2  # TV: -80%
        net += self.cinema * 0.2  # Cinema: -80%
        net += self.radio * 0.3  # Radio: -70%
        net += self.outdoor_static * 0.5  # Outdoor: -50%
        net += self.billboard * 0.5  # Billboard (outdoor): -50%
        net += self.internet * 0.5  # Internet: assume -50%
        net += self.magazines * 0.5  # Magazines: assume -50%
        net += self.newspapers * 0.5  # Newspapers: assume -50%
        net += self.indoor_tv * 0.5  # Indoor TV: assume -50%
        
        return net

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=True)
    agency_crm_id = db.Column(db.Integer, nullable=True)  # Track source contact ID from Agency CRM
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    linkedin_url = db.Column(db.String(500))
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    added_by = db.relationship('User', backref='added_contacts')
    activities = db.relationship('Activity', backref='contact', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_related_advertisers(self):
        """Get all advertisers related to this contact (primary + relationships via activities)"""
        # Start with primary advertiser if it exists
        related_advertisers = []
        if self.advertiser:
            related_advertisers.append(self.advertiser)
        
        # Find other advertisers mentioned in contact relationship activities
        filter_conditions = [
            Activity.description.contains(f"Contact relationship established: {self.first_name} {self.last_name}")
        ]
        
        # Only exclude primary advertiser if it exists
        if self.advertiser_id:
            filter_conditions.append(Activity.advertiser_id != self.advertiser_id)
        
        contact_activities = Activity.query.filter(*filter_conditions).all()
        
        for activity in contact_activities:
            if activity.advertiser not in related_advertisers:
                related_advertisers.append(activity.advertiser)
        
        return related_advertisers

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=True)  # Optional contact reference
    activity_type = db.Column(db.String(50), nullable=False)  # call, email, meeting, note
    description = db.Column(db.Text)
    outcome = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attachments = db.relationship('Attachment', backref='activity', lazy='dynamic')

class LeadStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    uploaded_by = db.relationship('User', backref='uploaded_attachments')

class Webhook(db.Model):
    """Webhook configuration for outgoing notifications"""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    events = db.Column(db.JSON, nullable=False)  # List of events to trigger webhook
    secret = db.Column(db.String(255), nullable=False)  # Secret for signature
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    logs = db.relationship('WebhookLog', backref='webhook', lazy='dynamic')

class WebhookLog(db.Model):
    """Log of webhook calls"""
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey('webhook.id'), nullable=False)
    event = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON)
    response_status = db.Column(db.Integer)
    response_body = db.Column(db.Text)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)