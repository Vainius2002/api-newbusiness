from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

class ActivityForm(FlaskForm):
    activity_type = SelectField('Activity Type',
                              choices=[
                                  ('call', 'Phone Call'),
                                  ('email', 'Email'),
                                  ('meeting', 'Meeting'),
                                  ('note', 'Note')
                              ],
                              validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    outcome = StringField('Outcome', validators=[Optional()])
    attachment = FileField('Attachment', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'], 'Only PDF, DOC, DOCX, TXT, and image files allowed!')
    ])
    submit = SubmitField('Save Activity')