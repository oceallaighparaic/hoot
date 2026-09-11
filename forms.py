from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import InputRequired, EqualTo
from flask_wtf.file import FileField, FileAllowed, FileRequired

class RegisterForm(FlaskForm):
    username = StringField("Username:", validators=[InputRequired()])
    password = PasswordField("Password:", validators=[InputRequired()])
    password2 = PasswordField("Confirm Password:", validators=[EqualTo("password")])

    submit = SubmitField("Sign Up")

class LoginForm(FlaskForm):
    username = StringField("Username:", validators=[InputRequired()])
    password = PasswordField("Password:", validators=[InputRequired()])

    submit = SubmitField("Log In")

# https://flask-wtf.readthedocs.io/en/1.2.x/form/?highlight=filefield
class EditUserForm(FlaskForm):
    image = FileField("Upload Image:", validators=[FileRequired(), FileAllowed(["jpg","jpeg","png"])])
    
    submit = SubmitField("Edit PFP")