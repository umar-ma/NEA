from datetime import datetime
from application import db, login_manager, app, bcrypt
from flask_login import UserMixin, current_user
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, AdminIndexView
from flask import redirect, url_for, request, flash

from sqlalchemy import event

import stripe


# ALL THE DATABASE MODELS CREATED ARE SELF-EXPLANATORY AS TO WHAT THEY STORE

# LOADS THE USER
@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(20), nullable=False)
    surname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)
    # backref allows you to access the whole table from another(post) table
    products = db.relationship('Product', backref='Owner', lazy=True)
    comments = db.relationship('Comment', backref='Owner', lazy=True)
    cart = db.relationship('Cart', backref='Owner', lazy=True)
    order = db.relationship('Order', backref='Owner', lazy=True)
    
    def __repr__(self):
        return f"User('{self.firstname}','{self.surname}','{self.email}')"


# IF A PASSWORD IS SET, THE PASSWORD IS HASHED BEFORE BEING SAVED TO THE DATABASE
@event.listens_for(User.password, 'set', retval=True)
def hash_user_password(target, value, oldvalue, initiator):
    if value != oldvalue:
        return bcrypt.generate_password_hash(value).decode('utf-8')
    return value



class Product(db.Model):

    __searchable__ = ['name', 'description']

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_product_id = db.Column(db.VARCHAR, nullable=False)
    stripe_price_id = db.Column(db.VARCHAR, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    date_set = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    description = db.Column(db.String(1000))
    deleted = db.Column(db.Boolean, default=False, nullable=False)
    comments = db.relationship('Comment', backref='Product', lazy=True)
    cart = db.relationship('Cart', backref='Product', lazy=True)
    order = db.relationship('Order', backref='Product', lazy=True)

    def __repr__(self):
    	return f"Product({self.name}','{self.price}','{self.date_set}','{self.image_file}')"


# IF A PRODUCT IS CREATED OR UPDATED, stripe_price IS CREATED FOR THE STRIPE ACCOUNT FOR THE PRODUCT
@event.listens_for(Product.price, 'set', retval=True)
def set_product_price(target, value, oldvalue, initiator):
    if float(value) != float(oldvalue):
        price = float(value)
        price = "{:.2f}".format(price)
        price = int(float(price)*100)
        stripe_price = stripe.Price.create(product=target.stripe_product_id, unit_amount=price, currency='gbp')
        target.stripe_price_id = stripe_price.id
        return value
    return oldvalue

# IF A PRODUCT NAME IS UPDATED, THE PRODUCT IS ALSO UPDATED IN THE STRIPE ACCOUNT
@event.listens_for(Product.name, 'set', retval=True)
def set_product_name(target, value, oldvalue, initiator):
    if value != oldvalue:
        stripe.Product.modify(
        target.stripe_product_id,
        name=value,
        description=target.description,
        )
        return value
    return oldvalue


class Comment(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date_set = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comment = db.Column(db.VARCHAR, nullable=False)
    
    def __repr__(self):
    	return f"Comment({self.comment}','{self.date_set}')"

class Cart(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)


class Address(db.Model): # session id not needed

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.VARCHAR, nullable=False)
    homeNumber = db.Column(db.String(4), nullable=False)
    streetAddr = db.Column(db.VARCHAR, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    postcode = db.Column(db.String(8), nullable=False)
    order = db.relationship('Order', backref='Address', lazy=True)

    def __repr__(self):
    	return f"Address({self.homeNumber}','{self.streetAddr}','{self.country}','{self.city}','{self.postcode}')"

class Payment(db.Model): # linked to order
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.VARCHAR, nullable=False)
    customer = db.Column(db.VARCHAR, nullable=False)
    payment_intent = db.Column(db.VARCHAR, nullable=False)
    payment_status = db.Column(db.String(10), nullable=False)
    date_bought = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    customer_email = db.Column(db.String(120), nullable=False)
    currency = db.Column(db.String(20), nullable=False)
    discount = db.Column(db.Integer, nullable=False)##########
    total = db.Column(db.Float(), nullable=False)
    order = db.relationship('Order', backref='Payment', lazy=True)

    def __repr__(self):
    	return f"Payment({self.customer_email}','{self.currency}','{self.total}','{self.date_bought}')"
 
class Order(db.Model): # linked to payment and order and user if user

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float(), nullable=False)

    def __repr__(self):
    	return f"Order({self.product_name}','{self.price}','{self.quantity}','{self.subtotal}')"


class Coupon(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    stripe_coupon_id = db.Column(db.VARCHAR, nullable=False)
    stripe_promocode_id = db.Column(db.VARCHAR, nullable=False)
    promocode = db.Column(db.VARCHAR, nullable=False)
    name_coupon = db.Column(db.String(100), nullable=False)
    amount_off = db.Column(db.Integer, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    max_redemptions = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expired = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
    	return f"Coupon({self.name_coupon}','{self.promocode}','{self.amount_off}','{self.duration_months}','{self.max_redemptions}','{self.created}','{self.expired}')"


# MODELVIEWS FOR ADMIN ARE CREATED FOR ADMIN TO ACCESS CERTAIN TABLES IN DATABASE AND UPDATE THEM
# THESE ADMIN MODEL-VIEWS ARE SELF-EXPLANATORY IN THEIR FUNCTION AND ARE A LIST OF ITEMS IN THE TABLE IN THE DATABASE WHICH CAN BE CREATED, SEARCHED, UPDATED,
# AND DELETED BY THE ADMIN

class MyAdminIndexView(AdminIndexView):
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):

        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))


class MyUserModelView(ModelView):
    
    page_size = 10
    can_delete = False
    
    
    column_searchable_list = ['email']
    column_filters = ['firstname' ,'surname', 'email']
    form_excluded_columns = ['products', 'comments', 'cart', 'order', 'image_file']

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))


class MyProductModelView(ModelView):
    
    page_size = 10
    can_delete = False


    column_exclude_list = ['stripe_product_id', 'stripe_price_id',]
    column_searchable_list = ['name']
    column_filters = ['name' ,'description']
    form_excluded_columns = ['comments', 'cart', 'order', 'stripe_product_id', 'stripe_price_id', 'image_file', 'date_set']
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))

class MyCommentModelView(ModelView):
    
    page_size = 10
    can_create = False
    can_edit = False


    column_searchable_list = ['comment']
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))

class MyCartModelView(ModelView):
    
    page_size = 10
    can_create = False
    can_edit = False
    can_delete = False
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))

class MyAddressModelView(ModelView):
    
    page_size = 10
    can_create = False
    can_delete = False


    column_exclude_list = ['session_id', ]
    column_searchable_list = ['streetAddr']
    column_filters = ['homeNumber', 'streetAddr', 'country', 'city', 'postcode']
    form_excluded_columns = ['order', 'session_id']
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))


class MyPaymentModelView(ModelView):
    
    page_size = 10
    can_create = False
    can_edit = False
    can_delete = False


    column_exclude_list = ['session_id', ]
    column_searchable_list = ['customer_email']
 


    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))

class MyOrderModelView(ModelView):
    
    page_size = 10
    can_create = False
    can_edit = False
    can_delete = False


    column_searchable_list = ['product_name']
    
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))


class MyCouponModelView(ModelView):

    can_create = False
    can_edit = False
    
    page_size = 10
    
    column_exclude_list = ['stripe_coupon_id', 'stripe_promocode_id', ]
    column_searchable_list = ['name_coupon']
    column_filters = ['name_coupon' ,'promocode']
    

    def is_accessible(self):
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        
        flash("Please log in as an admin to access this page", "info")
        return redirect(url_for('login', next=request.url))

# CREATING THE ADMIN PAGE
admin = Admin(app, index_view=MyAdminIndexView(), template_mode='bootstrap4')

# ADDING ALL THE ADMIN VIEWS THAT ADMIN CAN ACCESS TO THE ADMIN PAGE
admin.add_view(MyUserModelView(User, db.session))
admin.add_view(MyProductModelView(Product, db.session))
admin.add_view(MyCommentModelView(Comment, db.session))
admin.add_view(MyCartModelView(Cart, db.session))
admin.add_view(MyAddressModelView(Address, db.session))
admin.add_view(MyPaymentModelView(Payment, db.session))
admin.add_view(MyOrderModelView(Order, db.session))
admin.add_view(MyCouponModelView(Coupon, db.session))




