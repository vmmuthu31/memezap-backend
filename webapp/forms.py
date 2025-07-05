"""
Form definitions for the webapp.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import InputRequired, Length, Optional, ValidationError
from flask import session, request

class MemeForm(FlaskForm):
    """Form for generating memes."""
    image = FileField(
        'Upload Image', 
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
        ]
    )
    
    top_text = StringField(
        'Top Text',
        validators=[Optional(), Length(max=100)]
    )
    
    bottom_text = StringField(
        'Bottom Text',
        validators=[Optional(), Length(max=100)]
    )
    
    additional_text = TextAreaField(
        'Additional Text',
        validators=[Optional(), Length(max=500)],
        description="Additional text to be placed on the meme (optional)"
    )
    
    submit = SubmitField('Generate Meme')

class ChatForm(FlaskForm):
    """Form for the chat interface."""
    message = TextAreaField(
        'Message', 
        validators=[InputRequired(), Length(max=500)]
    )
    
    image = FileField(
        'Attach Image', 
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
        ]
    )
    
    submit = SubmitField('Send') 