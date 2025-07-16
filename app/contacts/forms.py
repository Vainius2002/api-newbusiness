from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Optional, URL

class ContactForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])
    linkedin_url = StringField('LinkedIn Profile URL', validators=[Optional(), URL()])
    submit = SubmitField('Save Contact')