from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from application.models import User

# CREATING ALL THE FORMS
# THE FORMS CREATED ARE SELF-EXPLANATORY

class RegistrationForm(FlaskForm):


    firstname = StringField('First Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    surname = StringField('Surname',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
                        
    password = PasswordField('Password', validators=[DataRequired()])

    confirm_password = PasswordField('Confirm_Password',
                                     validators=[DataRequired(), EqualTo('password')])


    submit = SubmitField('Sign Up')
	

    def validate_email(self, email):
        
        # CHECK THAT A VALID EMAIL IS ENTERED, WHICH HAS NOT ALREADY BEEN TAKEN BY ANOTHER USER
    	user = User.query.filter_by(email=email.data).first()		
    	if user:
    	    raise ValidationError('that email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    
    password = PasswordField('Password', validators=[DataRequired()])

    remember = BooleanField('Remember Me')

    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):

    
    firstname = StringField('First Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    surname = StringField('Surname',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])  


    submit = SubmitField('Update')
	

    def validate_email(self, email):
        
        # IF EMAIL IS CHANGED, CHECK NEW EMAIL IS NOT ALREADY TAKEN BY ANOTHER USER
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()		
            if user:
                raise ValidationError('that email is taken. Please choose a different one.')


class ProductForm(FlaskForm):

    name = StringField('Product Name',
                           validators=[DataRequired(), Length(min=2, max=40)])
    price = StringField('Price £', validators=[DataRequired(), Length(min=1)])
    quantity = IntegerField('Quantity Available', validators=[DataRequired(), NumberRange(min=1, max=999)])
    picture = FileField('Product Picture', validators=[FileAllowed(['jpg', 'png'])])
    description = TextAreaField('Description', widget=TextArea(), render_kw={'rows': 5})
    submit = SubmitField('Sell')

    def validate_price(self, price):

        # CHECK THAT A VALID PRICE IS ENTERED WHICH IS AN INTEGER OR A FLOAT
        a = price.data
        try:
            float(a)
        except:
            raise ValidationError('not a valid price. please enter a real number')
    
     


class SearchForm(FlaskForm):

    search = StringField('Product Name',
                           validators=[DataRequired(), Length(min=1)], render_kw={"placeholder": "What are you looking for?"})
    submit = SubmitField('Search')


class CommentForm(FlaskForm):

    comment = StringField('Comment',
                           validators=[DataRequired(), Length(min=1)],widget=TextArea(), render_kw={"placeholder": "Please leave a review ...", 'rows': 5})
    submit = SubmitField('Comment')
    
class AddressForm(FlaskForm):

    homeNumber = StringField('Home Number', validators=[DataRequired(), Length(min=1 ,max=4)])
    streetAddr = StringField('Street Address', validators=[DataRequired(), Length(min=1, max=50)])
    country = StringField('Country', validators=[DataRequired(), Length(min=1, max=50)])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=50)])
    postcode = StringField('Post Code', validators=[DataRequired(), Length(min=6, max=8)])
    checkout = SubmitField('Submit')

class UpdateProductForm(FlaskForm):

    name = StringField('Product Name',
                           validators=[DataRequired(), Length(min=2, max=40)])
    price = StringField('Price £', validators=[DataRequired(), Length(min=1)])
    quantity = IntegerField('Quantity Available', validators=[DataRequired(), NumberRange(min=1, max=999)])
    picture = FileField('Product Picture', validators=[FileAllowed(['jpg', 'png'])])
    description = TextAreaField('Description', widget=TextArea(), render_kw={'rows': 5})
    submit = SubmitField('Update Product')

    def validate_price(self, price):

        # CHECK THAT A VALID PRICE IS ENTERED WHICH IS AN INTEGER OR A FLOAT
        a = price.data
        try:
            float(a)
        except:
            raise ValidationError('not a valid price. please enter a real number')


class ChangeAboutForm(FlaskForm):

    content = StringField('Content',
                           validators=[DataRequired(), Length(min=1)],widget=TextArea(), render_kw={"placeholder": " ...", 'rows': 8})
    submit = SubmitField('Submit')


class CouponForm(FlaskForm):

    name = StringField('Coupon Name',
                           validators=[DataRequired(), Length(min=2, max=30)])
    amount_off = IntegerField('Amount Off £', validators=[DataRequired(), NumberRange(min=1, max=1000)])
    duration = IntegerField('Duration (Months)', validators=[DataRequired(), NumberRange(min=1, max=60)])
    max_redemptions = IntegerField('Maximum redemptions of Coupon', validators=[DataRequired(), NumberRange(min=1, max=1000)])

    submit = SubmitField('Create Coupon')
    
