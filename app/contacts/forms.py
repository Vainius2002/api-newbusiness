from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, URL
from wtforms.widgets import ListWidget, CheckboxInput

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class ContactForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])
    linkedin_url = StringField('LinkedIn Profile URL', validators=[Optional(), URL()])
    advertisers = MultiCheckboxField('Associated Advertisers', coerce=int)
    submit = SubmitField('Save Contact')
    
    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        from app.models import Advertiser
        self.advertisers.choices = [(a.id, a.name) for a in Advertiser.query.order_by(Advertiser.name).all()]
        
        # Initialize advertisers.data to empty list if None to prevent TypeError
        if self.advertisers.data is None:
            self.advertisers.data = []