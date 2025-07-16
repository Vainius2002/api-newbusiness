from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional
from app.models import Contact

class ActivityForm(FlaskForm):
    activity_type = SelectField('Activity Type',
                              choices=[
                                  ('call', 'Phone Call'),
                                  ('email', 'Email'),
                                  ('meeting', 'Meeting'),
                                  ('note', 'Note')
                              ],
                              validators=[DataRequired()])
    contact_id = SelectField('Contact (Optional)', coerce=int, validators=[Optional()])
    description = TextAreaField('Description', validators=[DataRequired()])
    outcome = StringField('Outcome', validators=[Optional()])
    attachment = FileField('Attachment', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'], 'Only PDF, DOC, DOCX, TXT, and image files allowed!')
    ])
    submit = SubmitField('Save Activity')
    
    def __init__(self, advertiser_id=None, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        if advertiser_id:
            # Get contacts for the advertiser
            contacts = Contact.query.filter_by(advertiser_id=advertiser_id).order_by(Contact.last_name, Contact.first_name).all()
            self.contact_id.choices = [(0, 'No specific contact')] + [(c.id, c.full_name) for c in contacts]
        else:
            self.contact_id.choices = [(0, 'No specific contact')]