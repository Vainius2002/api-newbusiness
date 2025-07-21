from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange
from app.models import User

class AdvertiserForm(FlaskForm):
    name = StringField('Advertiser Name', validators=[DataRequired()])
    current_agency = SelectField('Current Agency', 
                               choices=[
                                   ('', 'No Agency / Direct'),
                                   ('BPN (US) - IPG', 'BPN (US) - IPG'),
                                   ('Carat (Dentsu)', 'Carat (Dentsu)'),
                                   ('UM (Inspired) IPG', 'UM (Inspired) IPG'),
                                   ('Publicis media (Lion communications)', 'Publicis media (Lion communications)'),
                                   ('Initiate (Open agency) IPG', 'Initiate (Open agency) IPG'),
                                   ('Media House - Group M/WPP', 'Media House - Group M/WPP'),
                                   ('Arena media - Havas group', 'Arena media - Havas group'),
                                   ('Havas media - Havas group', 'Havas media - Havas group'),
                                   ('Vizeum/Dentsu X', 'Vizeum/Dentsu X'),
                                   ('Mindshare (Via media) - Group M/WPP', 'Mindshare (Via media) - Group M/WPP'),
                                   ('Mediacom (Trendmark) - Group M/WPP', 'Mediacom (Trendmark) - Group M/WPP'),
                                   ('Media brands digital - IPG', 'Media brands digital - IPG'),
                                   ('Omnicom (OMD/PHD)', 'Omnicom (OMD/PHD)'),
                                   ('Other medium digital', 'Other medium digital'),
                                   ('Other small digital', 'Other small digital')
                               ],
                               default='',
                               validators=[Optional()])
    lead_status = SelectField('Lead Status', 
                            choices=[
                                ('non_qualified', 'Non Qualified'),
                                ('ours', 'Ours'),
                                ('network', 'Network'),
                                ('cold', 'Cold Leads'),
                                ('get_info', 'Get Info'),
                                ('warm', 'Warm Leads'),
                                ('hot', 'Hot Leads'),
                                ('lost', 'Lost'),
                                ('non_market', 'Non-Market')
                            ],
                            default='non_qualified')
    assigned_user_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    submit = SubmitField('Save')
    
    def __init__(self, *args, **kwargs):
        super(AdvertiserForm, self).__init__(*args, **kwargs)
        self.assigned_user_id.choices = [(0, 'Unassigned')] + [
            (u.id, u.username) for u in User.query.order_by(User.username).all()
        ]

class LeadStatusForm(FlaskForm):
    new_status = SelectField('New Status', 
                           choices=[
                               ('non_qualified', 'Non Qualified'),
                               ('ours', 'Ours'),
                               ('network', 'Network'),
                               ('cold', 'Cold Leads'),
                               ('get_info', 'Get Info'),
                               ('warm', 'Warm Leads'),
                               ('hot', 'Hot Leads'),
                               ('lost', 'Lost'),
                               ('non_market', 'Non-Market')
                           ])
    reason = TextAreaField('Reason for Change', validators=[Optional()])
    submit = SubmitField('Update Status')

class BulkAssignForm(FlaskForm):
    user_id = SelectField('Assign To', coerce=int)
    submit = SubmitField('Assign Selected')
    
    def __init__(self, *args, **kwargs):
        super(BulkAssignForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [
            (u.id, u.username) for u in User.query.order_by(User.username).all()
        ]

class SpendingDataForm(FlaskForm):
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    cinema = FloatField('Cinema', default=0, validators=[Optional()])
    billboard = FloatField('Billboard', default=0, validators=[Optional()])
    indoor_tv = FloatField('Indoor TV', default=0, validators=[Optional()])
    internet = FloatField('Internet', default=0, validators=[Optional()])
    magazines = FloatField('Magazines', default=0, validators=[Optional()])
    newspapers = FloatField('Newspapers', default=0, validators=[Optional()])
    outdoor_static = FloatField('Outdoor Static', default=0, validators=[Optional()])
    radio = FloatField('Radio', default=0, validators=[Optional()])
    tv = FloatField('TV', default=0, validators=[Optional()])
    grand_total = FloatField('Grand Total (Gross)', default=0, validators=[Optional()])
    net_total = FloatField('Net Total', validators=[Optional()], description="Leave empty to calculate automatically")
    submit = SubmitField('Save Spending Data')