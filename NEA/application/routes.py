import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from application import app, db, bcrypt
from application.forms import RegistrationForm,LoginForm,UpdateAccountForm,ProductForm,SearchForm,CommentForm,AddressForm,UpdateProductForm,ChangeAboutForm,CouponForm
from application.models import User, Product, Comment, Cart, Address, Payment, Order, Coupon
from flask_login import login_user, current_user, logout_user, login_required
import requests
import stripe
from requests import get
import ast
from fuzzywuzzy import fuzz
from collections import defaultdict
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import smtplib




def create_db_if_not_exists():

    database_path = app.root_path + "/site.db" # FULL PATH OF THE DATABASE FILE
 
    if os.path.isfile(database_path): # CHECK IF DATABASE EXISTS
        print("Database exists")

    else:   
        db.create_all() # IF DATABASE DOESN'T EXIST, IT CREATES THE DATABASE BY ADDING ALL THE TABLES IN IT

create_db_if_not_exists()

# CREATING THE ADMIN USER
adm = User.query.filter_by(email='glamley08@gmail.com').first()
if not adm:
    admin = User(firstname='Glamley', surname='Glamley', email='glamley08@gmail.com', password='Testing@123', admin=True)
    db.session.add(admin)
    db.session.commit()



serializer = URLSafeTimedSerializer('5791628bb0b13ce0c676dfde280ba245') # apps secret key

app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_51I98vnDpZiqAHfHlBK9nm1SknZSiGVZf1JYVmOFiCo7OSfZmHaTdTJDUp6wjW02knoT8o5lqN7UeP4Kt4abqK7Rb0009V816hC'
app.config['STRIPE_SECRET_KEY'] = 'sk_test_51I98vnDpZiqAHfHl20FYk2bDfWfknVvXvU2a7RFwiYFcMELleIVMCCcOXdr6FUubGnPl8E7GpLNe2qvfCGmMeoWQ00iSZq9vGm'
stripe.api_key = app.config['STRIPE_SECRET_KEY']


@app.route("/")
@app.route("/home")
def home():

    return render_template("home.html",title="Home") 


@app.route("/about")
def about():

    with open("about.txt", "r") as f: # FILE OPENED AS CONTEXT MANAGER WHICH MAKE IT SO THE FILE IS CLOSED WITHOUT ANY ERRORS
        content = f.read() # READS THE FILES CONTENT TO SHOW IT ON THE TEMPLATE
        f.close()

    return render_template("about.html", title='About', content=content)


@app.route("/change_about", methods=['GET','POST'])
@login_required
def change_about():

    if current_user.admin == False: # IF USER IS NOT ADMIN, REDIRECT ELSEWHERE
        flash("You need to log in as an admin to access this page", "info")
        return redirect(url_for("home"))

    form = ChangeAboutForm()

    if request.method == 'POST': # IF POST REQUEST, GET FORM CONTENT AND OPEN AND WRITE IT ON THE ABOUT FILE
        if form.validate_on_submit:
            content = request.form.get('content')

            with open("about.txt", "w") as f:  # FILE OPENED AS CONTEXT MANAGER WHICH MAKE IT SO THE FILE IS CLOSED WITHOUT ANY ERRORS
                f.write(content) # WRITES ON THE FILE
                f.close() 

            return redirect(url_for("about"))

    elif request.method == 'GET': # IF GET REQUEST, READ FROM ABOUT FILE AND HAVE IT'S CONTENT SHOWN ON THE FORM
        
        with open("about.txt", "r") as f:
                text = f.read()
                form.content.data = text
                f.close()


    return render_template("change_about.html", title='Change About', form=form)
    


@app.route("/register", methods=['GET','POST'])
def register():

    if current_user.is_authenticated: # IF A USER IS ALREADY LOGGED IN, PAGE UNACCESABLE, REDIRECT ELSEWHERE
        return redirect(url_for('home'))

    form = RegistrationForm()

    if form.validate_on_submit(): # IF THE FORM IS FILLED VALIDLY
        #hashed_password = #bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(firstname=form.firstname.data, surname=form.surname.data, email=form.email.data, password=form.password.data) # CREATE USER
        db.session.add(user) # ADD THE RECORD TO THE DATABASE
        db.session.commit() # SAVE TO THE DATABASE
        flash('Your account has been created! You are now able to log in', 'success') # message and assigned category of message
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET','POST'])
def login():

    if current_user.is_authenticated: # IF USER ALREADDY LOGGED IN, REDIRECT
        return redirect(url_for('home'))

    form = LoginForm()

    if form.validate_on_submit(): # IF FORM FILLED VALIDLY
        user = User.query.filter_by(email=form.email.data).first() # QUERY A USER
        if user and bcrypt.check_password_hash(user.password, form.password.data): # IF A USER EXISTS AND PASSWORD MATCHES PASSWORD IN DATABASE
            login_user(user, remember=form.remember.data) # LOG THE USER IN
            next_page = request.args.get('next') # GETS THE ARGUEMENTS FOR THE NEXT PAGE IF ARGUEMENTS
            flash('Welcome ' + user.firstname, 'info') 
            return redirect(next_page) if next_page else redirect(url_for('home')) # REDIRECTS TO NEXT PAGE IF NEXT PAGE, ELSE TO HOME
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger') # shows an unsuccessful message

    return render_template('login.html', title='Login', form=form)
	

@app.route("/logout")
@login_required
def logout():

    if current_user.is_authenticated: # IF A USER IS LOGGED IN, LOG HIM OUT
        logout_user()
        flash('Logout Successful','info')
    else:
        flash('You are not logged in','danger')

    return redirect(url_for('home'))


def save_profile_picture(form_picture): ###1

    random_hex = secrets.token_hex(8)  # generates a random hex string to be our image name
    _, f_ext = os.path.splitext(form_picture.filename) # gets the filename and file extension seprately of image from your computer

    # combines hex and extension to create the new file name
    picture_fn = random_hex + f_ext 

    # joins the paths to have the new picture filename in the profile_pics directory
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn) 

    output_size = (125, 125) # size of new image
    i = Image.open(form_picture) # new variable opening form pic 
    i.thumbnail(output_size) # adjusting picture size
   
    i.save(picture_path) # saves the picture in the picture path
    
    return picture_fn


def save_product_picture(form_picture):

    random_hex = secrets.token_hex(8) 
    _, f_ext = os.path.splitext(form_picture.filename)

    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/product_pics', picture_fn)

    output_size = (300, 300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
   
    i.save(picture_path)
    
    return picture_fn



@app.route("/account", methods=['GET','POST'])
@login_required
def account():
    form = UpdateAccountForm()

    if request.method == 'POST': # IF THERE IS A POST REQUEST
        button_clicked = request.form.get('change_password') # GET WEATHER THE CHANGE PASSWORD UTTON WAS CLICKED
        if button_clicked:
            return redirect(url_for("change_password")) # IF CHNGE PASSWORD BUTTON CLICKED, REDIRECT TO change_password
        elif form.validate_on_submit(): # else IF change_password button ISN'T CLICKED AND THE FORM IS VALID
            if form.picture.data: # UPDATE USERS DETAILS IN THE DATABASE TO THE DETAILS THAT ARE CURRENTLY IN FORM
                picture_file = save_profile_picture(form.picture.data)
                current_user.image_file = picture_file
            current_user.firstname = form.firstname.data
            current_user.surname = form.surname.data
            current_user.email = form.email.data
            db.session.commit()
            flash("Your account has been updated!", "success")
            return redirect(url_for("account"))
        
    elif request.method == 'GET': # IF GET REQUEST IS SENT
        form.firstname.data = current_user.firstname # PUT IN FORM, USERS DETAILS FROM DATABASE
        form.surname.data = current_user.surname
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file) # IMAGE FILE FOR THE USER
    return render_template('account.html', title='Account', image_file=image_file, form=form)
	
	
@app.route("/sell", methods=['GET','POST'])
@login_required
def sell():
    form = ProductForm()

    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_product_picture(form.picture.data)
            product_pic = picture_file # IF PICTURE DATA, NAME OF PIC DATA
        else:
            product_pic = "default.jpg" # ELSE NAME OF PIC DATA


        price = float(form.price.data)
        price = "{:.2f}".format(price) # PRICE TO 2 D.P.
        #stripe_price = round(float(price),0)
        #stripe_price = int(stripe_price)*100
        stripe_price = int(float(price)*100)

        if form.description.data:
            stripe_product = stripe.Product.create(name=form.name.data, description=form.description.data)# CREATE A STRIPE PRODUCT WITH DESCRIPTION
        else:
            stripe_product = stripe.Product.create(name=form.name.data) # CREATE A STRIPE PRODUCT WITHOUT DESCRIPTION

        
        product = Product(stripe_product_id=stripe_product.id, name=form.name.data, price=price, quantity=form.quantity.data,
         image_file=product_pic, user_id=current_user.id, description=form.description.data)
        db.session.add(product)
        db.session.commit() # CREATE AND SAVE PRODUCT IN THE DATABASE
        flash('Product successfully added', 'success')
        return redirect(url_for('products'))

    form.quantity.data = 1 # FORM QUANTITY DATA IS 1 BY DEFAULT

    image_file = url_for('static', filename='product_pics/' + 'default.jpg') # DEFAULT IMAGE FILE OF THE PRODUCT

    return render_template("sell.html", title="Sell", form=form, image_file=image_file)

@app.route("/products", methods=['GET','POST'])
def products():


    form = SearchForm()
    page = request.args.get('page', 1, type=int) # GET THE PAGE ARGUEMENTS

    Filter = request.args.get("submit_button") # GET THE FILTER ARGUEMENT

    if not Filter:

        Filter_values = list(request.args.values())
        
        if len(Filter_values) > 1:
            Filter = Filter_values[1] # FILTER VALUE IF FILTER NOT FOUND DUE TO 2 ARGUEMENTS above, 
            
    print(Filter)
    

    if Filter: # DIFFERENT SORTS ACCORDING TO THE FILTER
        if Filter == "Ascending": # SORT IN ASCENDING ORDER OF NAME
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.name.asc()).paginate(page=page, per_page=8)
        elif Filter == "Descending": # SORT IN DESCENDING ORDER OF NAME
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.name.desc()).paginate(page=page, per_page=8)
        elif Filter == "Low to High": # SORT IN ASCESCENDING ORDER OF PRICE
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.price.asc()).paginate(page=page, per_page=8)
        elif Filter == "High to Low": # SORT IN DESCENDING ORDER OF PRICE
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.price.desc()).paginate(page=page, per_page=8)
        elif Filter == "Old to New":  # SORT IN ASCESCENDING ORDER OF DATE
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.date_set.asc()).paginate(page=page, per_page=8)
        elif Filter == "New to Old": # SORT IN DESCENDING ORDER OF DATE
            results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.date_set.desc()).paginate(page=page, per_page=8)
    else: # DEFAULT RESULTS GIVEN WITHOUOT ANY SORT/FILTER APPLIED
        results = Product.query.filter(Product.quantity >= 1).filter_by(deleted=False).order_by(Product.date_set.desc()).paginate(page=page, per_page=8)
    

    length_p = len(results.items)
    if request.method == 'POST': # UPON POST REQUEST, REDIRECT TO SEARCH RESULTS PAGE AS SEARCH IS INITIATED
        if form.validate_on_submit():
            return redirect(url_for("search_results",query=form.search.data, title="Products", form=form))
    
    button_clicked = request.form.get('submit_button')
    if button_clicked: # IF BUTTON CLICKED/FILTER APPLIED, REDIRECT BACK TO THIS PAGE WITH FILTER ARGUEMENT
        return redirect(url_for("products", title="Products", form=form))
    
    if Filter: # RENDER PAGE ACCORDING TO FILTER
        return render_template("products.html", title="Products", form=form, results=results, length_p=length_p, search=False, Filter=Filter)
    else:
        return render_template("products.html", title="Products", form=form, results=results, length_p=length_p, search=False)

@app.route("/products/search_results/<query>", methods=['GET','POST'])
def search_results(query):
    
    form = SearchForm()
    page = request.args.get('page', 1, type=int)

    Filter = request.args.get("submit_button")

    if not Filter:

        Filter_values = list(request.args.values())
        
        if len(Filter_values) > 1: # IF THERE IS A SORT FILTER, IT WOULD BE ON INDEX 1, AFTER PAGE ARGUEMENT, THUS A LENGTH OF 2
            Filter = Filter_values[1] # IF FILTER, FILTER=SORT
        
            

    search = "%{}%".format(query) # SEARCH QUERY FORMAT, SO IT CAN BE PUT IN QUERY for SQL
    results = set(Product.query.filter(Product.quantity >= 1, Product.name.like(search) | Product.description.like(search)).all()) # ALL THE PRODUCTS WITH SEARCH
    results2 = Product.query.filter(Product.quantity >= 1).all() # ALL THE VALID PRODUCTS
    
    r = []
    
    for i in results2: # COMPARING ALL PRODUCTS SIMILARITY TO SEARCH INPUT, AND GETTING THE RESULTS YOU WANT ACCORDING TO SIMILARITY
        if fuzz.token_set_ratio(i.name,query) >= 45:
            r.append(i)
        elif fuzz.token_set_ratio(i.description,query) >= 50:
            r.append(i)
        elif fuzz.partial_ratio(i.name.lower(),query.lower()) >= 80:
            r.append(i)

    results2 = set(r)

    results = list(results.union(results2)) # UNION METHOD SO RESULTS DONT OVERLAP WHEN COMBINED TO MAKE A BETTER SEARCH RESULT
    
    Product_ids = [] # GET IDS OFF ALL PRODUCTS YOU WANT ACCORDING TO THE SEARCH
    for result in results:
        Product_ids.append(result.id)
                                        
    results = tuple(Product_ids)
    
    if Filter == "Ascending": # GET ALL PRODUCTS SEARCHED WITH FILTER, IF FILTER
        print(Filter)
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.name.asc()).paginate(page=page, per_page=8)
    elif Filter == "Descending":
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.name.desc()).paginate(page=page, per_page=8)
        print(Filter)
    elif Filter == "Low to High":
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.price.asc()).paginate(page=page, per_page=8)
        print(Filter)
    elif Filter == "High to Low":
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.price.desc()).paginate(page=page, per_page=8)
        print(Filter)
    elif Filter == "Old to New":
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.date_set.asc()).paginate(page=page, per_page=8)
        print(Filter)
    elif Filter == "New to Old":
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.date_set.desc()).paginate(page=page, per_page=8)
        print(Filter)
    else: # DEFAULT PRODUCTS WITH NO FILTER
        results = Product.query.filter(Product.id.in_(results)).filter_by(deleted=False).order_by(Product.date_set.desc()).paginate(page=page, per_page=8)
    

    length = len(results.items)
    if form.validate_on_submit():
        return redirect(url_for("search_results",query=form.search.data, title="Products", form=form, length=length))
    elif request.method == 'GET':
        form.search.data = query # UPON GET REQUEST SET FORM SEARCH DATA TO THE QUERY YOU ENTERED SO IT CAN BE SEEN IN FORM

    if Filter: # SHOW PAGE FILTERED/SORTED ACCORDING TO USER
        return render_template("products.html", title="Search Results", form=form, results=results, length=length, search=True, Filter=Filter)
    else: # SHOW PAGE WITH DEFAULT SORT
        return render_template("products.html", title="Search Results", form=form, results=results, length=length, search=True)


@app.route("/product_description/<product_id>",  methods=['GET','POST'])
def product_description(product_id):

    form = CommentForm() # A FORM FOR COMMENTING ON PRODUCTS TO LEAVE A REVIEW
    product = Product.query.filter_by(id=product_id, deleted=False).filter(Product.quantity>0).first_or_404() # GET A VALID PRODUT THROUGH THE SELECTED PRODUCT'S ID
    comments = Comment.query.filter_by(product_id=product_id).order_by(Comment.date_set.desc()).all() # GET ALL THE COMMENTS FOR THAT PRODUCT TO DISPLAY
    
    if current_user.is_authenticated: # IF ITS A VALID USER, CHECK IF THE PRODUCT IS ALREADY IN USER'S CART
        cart = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first() # IF PRODUCT IS IN USERS CART, YOU WILL DISPLAY (REMOVE FROM CART) BUTTON
    else: # 
        cart = None # ELSE YOU WILL DISPLAY (ADD TO CART) BUTTON FOR THE PRODUCT

    # NO MATTER THE AMOUNT OF PRODUCTS AVAILABLE, LIMITING ALL USERS TO QUANTITY OF 8 OR LESS, THUS SETTING MAXIMUM TO 9 OR LESS.
    if product.quantity >= 9:
        maximum = 9
    else:
        maximum = product.quantity

    if request.method == 'POST': # IF THERE IS A POST REQUEST
        button_clicked = request.form.get('submit_button') # GET THE VALUE OF THE (SUBMIT BUTTON)

    

        if button_clicked:
            if request.form.get('quantity-selected') == "9+": # IF 9+ IS SELECTED IN QUANTITY
                flash("Your account is restricted to buying 8 products", "danger")  # ERROR MESSAGES TO RESTRICT QUANTITY OF PRODUCT TO 8 OR LESS
            else:
                if button_clicked == "Buy Now": # IF VALUE OF (BUTTON_CLICKED) IS (BUY NOW),
                    if current_user.is_authenticated:
                        if product.Owner.id == current_user.id: # IF THE (PRODUCT OWNER) IS THE SAME AS THE BUYER
                            flash("You can't buy your own product", "info") # ERROR MESSAGE THAT USER CAN'T BUY HIS OWN PRODUCTS
                        else:
                            return redirect(url_for("address",products=product_id, quantity=request.form.get('quantity-selected'))) # OTHERWISE, REDIRECT TO THE ADDRESS PAGE WITH APPROPRIATE ARGUEMENTS
                    else:
                        return redirect(url_for("address", products=product_id, quantity=request.form.get('quantity-selected'))) # OTHERWISE, REDIRECT TO THE ADDRESS PAGE WITH APPROPRIATE ARGUEMENTS
                if button_clicked == "Add to Cart": # IF THE (BUTTON_CLICKED) IS (ADD TO CART)
                    if current_user.is_authenticated:
                        if product.Owner.id == current_user.id: # IF (PRODUCT OWNER) IS THE SAME AS THE USER
                            flash("You can't add your own product to cart", "info") # DISPLAY ERROR MESSAGE THAT USER CAN'T ADD HIS OWN PRODUCT TO CART
                        else: # OTHERWISE, THE PRODUCT IS ADDED TO THE CART OF USER AND SAVED
                            cart = Cart(user_id=current_user.id, product_id=product_id) 
                            db.session.add(cart)
                            db.session.commit()
                            flash("Item successfully added to Cart", "success") # SUCCESS MESSAGE THAT PRODUCT SUCCESSFULLY ADDED TO CART
                            return redirect(url_for("product_description", product_id=product_id)) # REDIRECT BACK TO THE SAME PAGE TO REFRESH PAGE, SO NOW IT DISPLAYS (REMOVE FROM CART) INSTEAD OF (ADD TO CART)
                    else: # IF USER IS NOT LOGGED IN
                        flash("Please log in to add items to cart", "success") #USER IS UNABLE TO ADD PRODUCTS TO CART
                        return redirect(url_for("login")) # REDIRECTED TO LOGIN
                if button_clicked == "Remove from Cart": # IF THE (BUTTON_CLICKED) IS (REMOVE FROM CART)
                    if current_user.is_authenticated: # IF ITS A VALID/LOGGED IN USER
                        if cart: # IF THE PRODUCT IS ALREADY IN CART, (SINCE NEEDS TO BE IN CART BEFORE IT CAN BE DELETED FROM CART)
                            return redirect(url_for("delete_from_cart", product_id=product_id)) # REDIRECTED TO A PAGE WHICH DELETES THE PRODUCT FROM CART, AND BRINGS YOU BACK TO THIS PAGE

        else: # OTHERWISE
            if form.validate_on_submit(): # IF FORM IS SUBMITTED, YOU MUST BE COMMENTING
                if current_user.is_authenticated: # IF A VALID USER, SAVE THE COMMENT IN THE DATABASE
                    comment = Comment(user_id=current_user.id, product_id=product.id, comment=form.comment.data) 
                    db.session.add(comment)
                    db.session.commit()
                    return redirect(url_for("product_description", product_id=product_id)) # REDIRECT BACK TO THIS PAGE SO IT REFRESHES DISPLAYING ALL THE COMMENTS
                else: # ELSE
                    flash("You need to log in to leave a comment", "danger") # USER UNABLE TO COMMENT WITHOUT AN ACCOUNT 

    return render_template("product_description.html", title="Product-description", form=form, product=product, maximum=maximum, comments=comments, cart=cart) # RENDER THE PAGE WITH THE PRODUCT'S DESCRIPTION


@app.route("/buy/address/<products>/<quantity>", methods=['GET','POST'])  ###2
def address(products, quantity): # gets string

    form = AddressForm() # FORM TO FILL IN ADDRESS
    
    if products == 'Cart': # IF WE REDIRECTED FROM CARTS PAGE,
        products_using = Cart.query.filter_by(user_id=current_user.id).all() # GET ALL THE PRODUCTS FROM USERS CART
    else: # ELSE IF REDIRECTED FROM (PRODUCTS_DESCRIPTION) PAGE
        # GET THE PRODUCT FROM ID 
        products_using = Product.query.filter_by(id=products, deleted=False).filter(Product.quantity>0).first_or_404() 

    # ADD ALL THE PRODUCTS YOU ARE BUYING TO THE (PRODUCT_LIST)
    product_list = []
    if products == 'Cart':
        for product in products_using:
            p = Product.query.filter_by(id=product.product_id, deleted=False).filter(Product.quantity>0).first()
            product_list.append(p)
    else:
        p = products_using
        product_list.append(p)

    # ADDING ALL THE QUANTITIES IN (QUANTITY_LIST), PRODUCT AND ITS SELECTED QUANTITY WILL BE ON SAME INDEX IN ITS CORRESPONDING LIST
    quantity_list = []
    if products == 'Cart':
        for i in quantity:
            try:
                int(i)
                quantity_list.append(int(i))
            except:
                pass
    else:
        quantity_list.append(int(quantity))

    
    loc = get('https://ipapi.co/json/') # USING AN API TO GET APPROXIMATE CURRENT LOCATION
    data = loc.json()  # CONVERTS loc WHICH IS A STRING TO A DICTIONARY


    if request.method == 'POST': # IF ITS A POST REQUEST
        if form.validate_on_submit(): # IF FORM IS VALIDLY SUBMITTED

            # ADDING A LIST OF DICTIONARY WITH (STRIPE_PRICE_ID) FOR price AND (QUANTITY) for quantity, WHICH IS THE FORMAT REQUIRED FOR STRIPE
            list_for_session = []
            for i in range(0, len(product_list)):
                list_for_session.append({'price': product_list[i].stripe_price_id, 'quantity': quantity_list[i]})
            
            addr = {"homeNumber": form.homeNumber.data, "streetAddr": form.streetAddr.data, "country": form.country.data, 
            "city": form.city.data, "postcode": form.postcode.data} # ALL OF THE ADDRESS DATA IN A DICTIONARY

            # CREATING THE STRIPE SESSION WITH (list_for_session) CREATED ABOVE IN STRIPE FORMAT, AND A SUCCESS AND A CANCEL URL
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=list_for_session,
                mode='payment',
                allow_promotion_codes=True,
                success_url=url_for('thanks',addr=addr, _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('home', _external=True),
            )      
            
            # RENDERS THE TEMPLATE AGAIN WITH THE APPROPRIATE ARGUEMENTS NEEDED TO GO TO STRIPE CHECKOUT PAGE
            return render_template(
                'address.html', title='Address details', form=form,
                checkout_session_id=session['id'], 
                checkout_public_key=app.config['STRIPE_PUBLIC_KEY']
            )
                   
        else: # OTHERWISE
            flash("Invalid form", "danger") # ERROR MESSAGE AS FORM NOT FILLED VALIDLY

    if request.method == 'GET': # IF ITS A GET REQUEST, AUTOFILL SOME PART/S OF THE ADDRESS
        print(data)
        form.country.data = data['region']
        form.city.data = data['city']

    return render_template("address.html", title='Address details', form=form) # RENDERS THE PAGE

class Stack():

    def __init__(self):
        self.array = []

    def push(self, item):
        self.array.append(item)
        return item

    def pop(self):

        if self.isempty():
            return None
        
        return self.array.pop()

    def peek(self):
        if self.isempty():
            return None
        
        return self.array[-1]
        
    def items(self):
        return self.array

    def size(self):
        return len(self.array)

    def isempty(self):
        if self.array == []:
            return True
        return False

@app.route("/cart", methods=['GET','POST'])
@login_required
def cart():

    items = Cart.query.filter_by(user_id=current_user.id).all() # GETS ALL THE ITEMS IN THE USER'S CART
    products_stack = Stack()
    products = []
    if items:
        for item in items:
           
            product = item.Product # GETTING THE PRODUCT ASSOCIATED WITH THAT ITEM IN CART 
            if product.quantity <= 0 or product.deleted == True: # IF A PRODUCT IS INVALID, DELETE IF FROM CART
                db.session.delete(item)
                db.session.commit()
            else:
                products_stack.push(product) # ELSE, PUSH THE PRODUCT INTO THE STACK
    
    if products_stack.isempty() == False: # IF STACK IS NOT EMPTY
        # ALL THE PRODUCTS ARE POPPED FROM STACK INTO products LIST SO THEY ARE REVERSED, TO DISPLAY PRODUCTS IN CART FROM RECENTLY ADDED TO CART TO OLD
        for i in range(products_stack.size()):
            products.append(products_stack.pop())
    

    if request.method == 'POST': # IF THERE IS A POST REQUEST
        if request.form.get('to-checkout') == "Proceed to Checkout": # IF (PROCEED TO CHECKOUT) BUTTON IS CLICKED
            quantity_stack = Stack() 
            quantity_list = []          
            for p in products: # PUSH ALL QUANTITIES INTO STACK 
                quantity_stack.push(request.form.get(p.stripe_product_id))

            if quantity_stack.isempty() == False: # IF STACK IS NOT EMPTY
                # ALL QUANTITIES ARE POPPED INTO (QUANTITY_LIST) TO REVERSE THEM,
                # SO THE INDEX OF QUANTITY SELECTED FOR A PRODUCT IS IN THE SAME INDEX AS THE PRODUCT IN THEIR CORRESPONDING LIST
                for i in range(quantity_stack.size()): 
                    quantity_list.append(quantity_stack.pop())
            
            return redirect(url_for('address', products='Cart', quantity=quantity_list)) # REDIRECT TO ADDRESS PAGE
            

    return render_template("cart.html", title='Cart', products=products) # RENDER THE cart PAGE

@app.route("/cart/delete/product/<int:product_id>")
@login_required
def delete_from_cart(product_id):

    # GET THE CART ITEM SELECTED THROUGH ID AND DELETE IT
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404() 
    db.session.delete(item)
    db.session.commit()
    flash("Item successfully deleted from cart", "success") # SUCCESSFULLY DELETED ITEM FROM CART
    return redirect(url_for("cart")) # REDIRECT TO CART 
    


@app.route("/cart/empty/products/")
@login_required
def empty_cart():

    items = Cart.query.filter_by(user_id=current_user.id).all() # GET ALL ITEMS IN CART OF THE USER

    # FOR EACH ITEM IN CART, DELETE IT
    if items:
        for item in items:         
            db.session.delete(item)
        db.session.commit() 
        flash("Your Cart has been Successfully emptied", "success") # SUCCESS MESSAGE THAT CART HAS BEEN EMPTIED
    else:
        flash("Your cart is already empty", "info") # MESSAGE THAT CART IS ALREADY EMPTY

    return redirect(url_for("cart")) # REDIRECT TO CART


@app.route('/thanks/<addr>')
def thanks(addr):

    address = ast.literal_eval(addr) # CONVERTS THE ADDRESS(addr) INTO A DICTIONARY
    session_id = request.args.get("session_id") # GET THE session_id FROM THE ARGUEMENTS OF THIS PAGE
    
    already_paid_indb = Payment.query.filter(Payment.session_id==session_id).first() # CHECK IF PAYMENT HAS NOT ALREADY BEEN MADE IN THIS SESSION
    if not already_paid_indb: # IF PAYMENT HAS NOT BEEN ADE
        session = stripe.checkout.Session.retrieve(session_id) # RETRIEVE THE STRIPE SESSION THROUGH THE session_id
        line_items = stripe.checkout.Session.list_line_items(session_id) # RETRIEVE THE ITEMS YOU ARE BUYING IN THIS SESSION

        
        for item in line_items: # FOR EACH ITEM YOU ARE BUYING
            price = item['price']['id'] # GET ITS (STRIPE_PRICE_ID)
            quantity_bought = item['quantity'] # GET ITS QUANTITY YOU ARE BUYING
            p = Product.query.filter_by(stripe_price_id=price).first() # GET THE PRODUCT YOU ARE BUYING FROM THE DATABASE USING (STRIPE_PRICE_ID)
            p.quantity = p.quantity - quantity_bought # UPDATE ITS QUANTITY BY DECREASING IT BY THE AMOUNT YOU ARE BUYING
        db.session.commit() # SAVE THESE CHANGES IN THE DATABASE

        #----------------

        # SAVING THE PAYMENT MADE INTO DATABASE
        payment = Payment(session_id=session_id, customer=session['customer'], payment_intent=session['payment_intent'],
         payment_status=session['payment_status'], customer_email=session['customer_details']['email'] , currency=session['currency'],
          discount=session['total_details']['amount_discount']/100, total=session['amount_total']/100)
        # SAVING THE ADDRESS OF CUSTOMER INTO DATABASE
        address = Address(session_id=session_id ,homeNumber=address['homeNumber'], streetAddr=address['streetAddr'],
         country=address['country'], city=address['city'], postcode=address['postcode'])
        db.session.add(payment)
        db.session.add(address)
        db.session.commit() # SAVE THE PAYMENT DETAILS AND THE ADDRESS INTO DATABASE OF CUSTOMER
        

        pay = Payment.query.filter_by(session_id=session_id).first() # GET THE PAYMENT CUSTOMER MADE IN DATABASE
        addr = Address.query.filter_by(session_id=session_id).first() # GET THE ADDRESS OF CUSTOMER IN DATABASE
        
        # FOR EACH ITEM YOU ARE BUYING, SAVE THE ORDER DETAILS MADE INTO DATABASE WITH (PAYMENT ID) AND (ADDRESS ID) AS FOREIGN KEYS
        for item in line_items:
            product = stripe.Product.retrieve(item['price']['product'])
            product_id = Product.query.filter_by(stripe_price_id=item['price']['id']).first_or_404()
            product_id = product_id.id
            if current_user.is_authenticated:
                order = Order(payment_id=pay.id , address_id=addr.id, user_id=current_user.id, product_id=product_id,
                 product_name=product['name'], price=item['price']['unit_amount']/100, quantity=item['quantity'], subtotal=item['amount_subtotal']/100)
            else:
                order = Order(payment_id=pay.id , address_id=addr.id, product_id=product_id, product_name=product['name'],
                 price=item['price']['unit_amount']/100, quantity=item['quantity'], subtotal=item['amount_subtotal']/100)

            db.session.add(order)
        db.session.commit() # SAVE THE CHANGES MADE INTO DATABASE

    else: # ELSE ALL THE PAYMENT, ORDER AND ADDRESS HAVE ALREADY BEEN SAVED TO DATABASE
        flash("Session already Completed", "info") # MESSAGE THAT TRANSACTION HAS ALREADY BEEN COMPLETED
    
    
    
    pay = Payment.query.filter_by(session_id=session_id).first()

    orders = Order.query.filter_by(payment_id=pay.id).all() # GETTING ALL ORDERS SO THEY CAN BE DISPLAYED IN THE thanks PAGE

    return render_template("thanks.html", title="Thanks Page", orders=orders) # RENDERS THE thanks PAGE

@app.route("/YourProducts")
@login_required
def your_products():

    # GETS ALL OF THE USERS PRODUCTS SO THEY CAN BE DISPLYED IN THIS PAGE  
    products =  Product.query.filter_by(user_id=current_user.id, deleted=False).order_by(Product.date_set.desc()).all()

    return render_template('your_products.html', title="Your Products", products=products) # RENDERS THE PAGE WITH ALL OF USER'S PRODUCTS



@app.route("/products/delete_all")
@login_required
def delete_all_products():

    products = Product.query.filter_by(user_id=current_user.id, deleted=False).all() # GETS ALL THE USER'S PRODUCTS

    # DELETES ALL THE USER'S PRODUCTS, AND IF THE PRODUCT IS IN SOMEONE'S CART, ALSO DELETES THE PRODUCTS FROM THE CART
    if products:
        for product in products:
            product.deleted = True
            cart = Cart.query.filter_by(product_id=product.id).all()
            if cart:
                for item in cart:
                    db.session.delete(item)

        db.session.commit() 
        flash("You Have Successfully deleted all Products", "success") 
    else:
        flash("There are no products to delete", "info")
 
    return redirect(url_for("your_products"))

@app.route("/product/delete/<int:product_id>")
@login_required
def delete_product(product_id):
    
    product = Product.query.filter_by(id=product_id, user_id=current_user.id, deleted=False).first_or_404() # GET THE PRODUCT TO BE DELETED
    cart = Cart.query.filter_by(product_id=product_id).all() # GET EACH cart the product is in
   
    # DELETES THE PRODUCT, AND ALSO DELETES PRODUCT IN ALL THE CARTS
    if product:
        product.deleted = True
        if cart:
            for item in cart:
                db.session.delete(item)  
        db.session.commit()
        flash("Product Successfully Deleted", "success")
    else:
        flash("Product not Found", "danger")

    return redirect(url_for("your_products"))

    
@app.route("/product/update/<int:product_id>", methods=['GET','POST'])
@login_required
def update_product(product_id):
    
    form = UpdateProductForm() # FORM FOR UPDATING PRODUCT
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404() # GET THE PRODUCT TO UPDATE
    #------
    if form.validate_on_submit(): # IF FORM IS VALIDLY SUBMITTED
        # IF THERE IS PICTURE DATA, SAVE THE PICTURE
        if form.picture.data:
            picture_file = save_product_picture(form.picture.data)
            product_pic = picture_file
        else: # ELSE PICTURE IS THE SAME AS BEFORE FOR THE PRODUCT
            product_pic = product.image_file

        # GET THE PRICE IN FORM TO 2 DECIMAL PLACES
        price = float(form.price.data)
        price = "{:.2f}".format(price)
        #stripe_price = int(float(price)*100)

        # MODIFY PRODUCT DETAILS IN THE STRIPE ACCOUNT
        stripe.Product.modify(
            product.stripe_product_id,
            name=form.name.data,
            description=form.description.data
        )

        # UPDATE AND SAVE THE NEW PRODUCT DETAILS
        product.name = form.name.data
        product.price = price
        product.quantity = form.quantity.data
        product.image_file = product_pic
        product.description = form.description.data
        db.session.commit()
        flash('Product successfully updated', 'success')

        return redirect(url_for('your_products')) # REDIRECT TO (your_products)
        
    if request.method == 'GET': # IF THERE IS A GET REQUEST
        # DISPLAY THE PRODUCTS CURRENT DATA IN THE FORM
        form.name.data = product.name
        form.price.data = product.price
        form.quantity.data = product.quantity
        form.description.data = product.description

    image_file = url_for('static', filename='product_pics/' + product.image_file) # GET THE IMAGE FILE OF THE PRODUCT
    #------
    return render_template("update_product.html",title="Update Product" , form=form, product=product, image_file=image_file) # RENDER THE (update_product) PAGE


@app.route("/orders")
@login_required
def your_orders():
    
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all() # GETS ALL THE USERS ORDERS
   
    groups = defaultdict(list)

    # groups the orders together with same payment id as they were bought together
    for order in orders:
        groups[order.Payment.id].append(order)


    orders = groups.values() # GETS JUST THE VALUES/ORDERS GROUPED IN LISTS WITH SAME PAYMENT ID SO ORDERS/PRODUCTS BOUGHT TOGETHER ARE DISPLAYED TOGETHER
   

    return render_template("your_orders.html", title="Your Orders", orders=orders) # RENDERS THE PAGE WITH THE USERS ORDERS


@app.errorhandler(404)
def page_not_found(e):

    # REDNDERS 404 PAGE FOR WHEN A PAGE OR ANY ITEM IN DATABASE IS NOT FOUND, INSTEAD OF GIVING AN ERROR AND STOPPING THE EXECUTION OF THE APPLICATION
    return render_template('404.html', error=e), 404


def send_mail(recipient, message, subject=''): ###3
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()

            smtp.login('glamley08@gmail.com', 'Testing@123') # LOGS IN TO THE GOOGLE ACCOUNT
           
            msg = 'Subject: {}\n\n{}'.format(subject, message) # CONTENTS OF THE MESSAGE AND SUBJECT OF MESSAGE IN FORMAT FOR EMAIL

            smtp.sendmail('glamley08@gmail.com', recipient, msg) # SENDS THE MAIL WITH MESSAGE TO THE RECIPIENT

            return True
    except:
        flash("There was an error sending an email. Please check your connection and try again", "danger") # ERROR MESSAGE FOR WHEN MESSAGE IS NOT SENT

@app.route('/password_forgotten', methods=['GET','POST'])
def password_forgotten():

    if request.method == 'POST':
        email = request.form['email'] # GET CUSTOMER'S EMAIL FROM FORM
        user = User.query.filter_by(email=email).first() # GET THE USER WITH THAT EMAIL

        if user: # IF USER EXISTS
            token = serializer.dumps(email, salt='password-reset')
            link = url_for("reset_password", token=token, _external=True) # LINK WITH TOKEN
            subject = 'Password Reset'
            body = 'Below is your password reset link. Use the link before it expires in 1 hour. The link is as following {}'.format(link)
            mail = send_mail(email, body, subject) # SEND A MAIL TO THAT EMAIL WITH LINK TO RESET PASSWORD
            if mail: # IF MAIL IS SUCCESSFULLY SENT, DISPLAY SUCCESSFUL MESSAGE
                flash("Email Successfully sent to " + email , "success")
        else: # ELSE, IF USER DOESN'T EXIST, DISPLAY ERROR MESSAGE
            flash("No Account Found for " + email + " in the database", "danger")
            

    return render_template("password_forgotten.html", title="Forgot Password") # RENDERS THE (password_forgotten) PAGE


@app.route('/password_reset/<token>', methods=['GET','POST'])
def reset_password(token): 

    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600) # LOADS THE TOKEN FROM THE LINK SENT TO EMAIL
    except SignatureExpired: # ERROR MESSAGE IF TOKEN HAS EXPIRED
        flash("Password reset link has expired. Please try again.", "info")
        return redirect(url_for("password_forgotten")) # REDIRECT TO (password_forgotten) PAGE
    except Exception as e: # ERROR MESSAGE FOR OTHER TYPES OF ERRORS
        flash("There was some sort of error in resetting your password. Please try again with a valid link", "info")
        return redirect(url_for("password_forgotten")) # REDIRECT TO (password_forgotten) PAGE

    user = User.query.filter_by(email=email).first_or_404() # GET THE USER WITH THAT EMAIL

    if request.method == 'POST': # IF THERE IS A POST REQUEST
       
        password = request.form['password'] # GET THE PASSWORD ON THE FORM
        
        # SET THE USER'S PASSWORD TO PASSWORD ON THE FORM ENTERED BY THE USER
        user.password = password
        db.session.commit()

        flash("Password Successfully Changed", "success")

        return redirect(url_for("login")) # REDIRECT TO LOGIN SO USER CAN LOG IN WITH NEW PASSWORD

    return render_template("password_reset.html", title="Reset Password") # RENDER THE (password_reset) PAGE
    


@app.route('/password_change', methods=['GET','POST'])
@login_required
def change_password():

    user = User.query.filter_by(id=current_user.id).first_or_404() # GET THE CURRENT USER

    if request.method == 'POST': # IF THERE IS A POST REQUEST

        current_password_form = request.form['current_password'] # GET THE PASSWORD ENTERED BY USER ON (CURRENT_PASSWORD) FORMM FIELD
        check = bcrypt.check_password_hash(user.password, current_password_form) # CHECK IF CURRENT PASSWORD OF USER AND CURRENT PASSWORD ENTERED BY USER ON FORM IS SAME
        if check: # IF THEY ARE THE SAME

            password = request.form['password'] # GET THE NEW PASSWORD ENTERED BY USER ON (NEW_PASSWORD) FIELD
            
            # UPDATE THE USERS PASSWORD
            user.password = password
            db.session.commit()

            flash("Password Successfully Changed", "success")
            
            return redirect(url_for("account")) # REDIRECT TO ACCOUNT PAGE
        else: # IF PASSWORD DOESN'T MATCH, DISPLAY ERROR MESSAGE
            flash("Current Password doesn't match your account's password", "danger")
            return redirect(url_for("change_password"))
        

    return render_template("change_password.html", title="Change Password") # RENDERS THE (change_password) PAGE



@app.route("/coupon/create", methods=['GET','POST'])
@login_required
def create_coupon():
    # IF CURRENT USER IS NOT AN ADMIN, REDIRECT TO HOME AS ONLY ADMIN CAN CREATE A COUPON
    if current_user.admin == False:
        flash("You need to log in as an admin to access this page", "info")
        return redirect(url_for("home"))

    form = CouponForm() # COUPON FORM

    if request.method == 'POST': # IF THERE IS A POST REQUEST

        if form.validate_on_submit(): # IF FORM IS VALIDLY SUBMITTED

            amount = form.amount_off.data * 100
            # A COUPON IS CREATED ACCORDING TO HOW A FORM IS FILLED-IN IN STRIPE
            coupon = stripe.Coupon.create(
                name=form.name.data,
                amount_off=amount,
                currency="gbp",
                duration="repeating",
                duration_in_months=form.duration.data,
                max_redemptions=form.max_redemptions.data,
            )

            # A PROMOCODE IS CREATED THROUGH THE COUPON
            promocode = stripe.PromotionCode.create(coupon=coupon.id)
            
            # THE COUPON IS SAVED IN THE DATABASE
            coupon_db = Coupon(stripe_coupon_id=coupon.id, stripe_promocode_id=promocode.id, promocode=promocode.code, name_coupon=coupon.name,
             amount_off=form.amount_off.data, duration_months=form.duration.data, max_redemptions=form.max_redemptions.data)
            db.session.add(coupon_db)
            db.session.commit()

            flash("Coupon Successfully created", "success")
            return redirect(url_for("send_coupon")) # REDIRECTED TO (send_coupon) PAGE
   
    return render_template("create_coupon.html", form=form, title="Coupon") # RENDERS THE (create_coupon) PAGE


@app.route("/coupon/send", methods=['GET','POST'])
@login_required
def send_coupon():
    
    # IF CURRENT USER IS NOT AN ADMIN, REDIRECT TO HOME AS ONLY ADMIN CAN CREATE A COUPON
    if current_user.admin == False:
        flash("You need to log in as an admin to access this page", "info")
        return redirect(url_for("home"))

    users = User.query.all() # GET ALL USERS
    length = len(users) # LENGTH OF ALL USERS

    coupons = Coupon.query.filter_by(expired=False).all() # GET ALL UNEXPIRED COUPONS
    length_coupon = len(coupons) # LENGTH OF COUPONS
    
    # FOR EACH COUPON CHECK IF ITS EXPIRED ON STRIPE, IF SO, THEN SET EXPIRED TO TRUE IN DATABASE
    for coupon in coupons:

        promocode = stripe.PromotionCode.retrieve(
            coupon.stripe_promocode_id,
        )

        if promocode['active'] == False:
            coupon.expired = True
            db.session.commit()

    coupons = Coupon.query.filter_by(expired=False).all() # GET ALL THE COUPONS IN THE DATABASE WHICH ARE NOT EXPIRED
    
    if request.method == 'POST': # IF THERE IS A POST REQUEST
        emails = request.form.get('list') # GET A LIST OF EMAILS OF USERS SELECTED TO SEND A COUPON TO
        coupon = request.form.get('coupon') # GET THE COUPON SELECTED

        if not emails: # IF THERE ARE NO EMAILS, NO USER IS SELECTED
            flash("No Users selected", "info")
            return redirect(url_for("send_coupon"))
        elif not coupon: # IF THERE IS NO COUPON, NO COUPON IS AVAILABLE TO BE SENT
            flash("No Coupon Available, Please ensure an active coupon is available before trying to send it", "info")
            return redirect(url_for("send_coupon"))
        else: # ELSE IF THERE IS A COUPON, AND USER OR USERS HAVE BEEN SELECTED
            email_list = emails.split(",") # GET A LIST OF ALL EMAILS, BY SEPRATING STRING WITH ,
            db_coupon = Coupon.query.filter_by(id=coupon).first() # GET THE COUPON SELECTED FROM DATABASE
            date = db_coupon.created.strftime("%B %d, %Y") # GET DATE THE COUPON EXPIRES
            link = url_for("home", _external=True) # LINK TO HOME PAGE OF THE WEBSITE
            msg = 'Congratulations! Be one of the first {} people to redeem this coupon and gain an  discount of {} pounds. The coupon code is {}. The coupon expires on {}. Please visit our website at {} and enter the code at checkout to redeem this coupon.'.format(db_coupon.max_redemptions,  db_coupon.amount_off, db_coupon.promocode, date, link)
            for email in email_list: # SEND A MAIL WITH COUPON TO EVERY USER SELECTED
                mail = send_mail(email, msg, 'Coupon') 
            if mail: # IF EMAIL SUCCESSFULLY SENT, SHOW A SUCCESSFIL MESSAGE
                flash("Email Successfully sent to all the selected users", "success")

        return redirect(url_for("send_coupon")) # REDIRECT TO (send_coupon) PAGE
    
    return render_template("send_coupon.html", title="Send Coupon", users=users, length=length, coupons=coupons, length_coupon=length_coupon) # RENDERS THE (send_coupon) PAGE


@app.route("/coupon", methods=['GET','POST'])
@login_required
def coupon():

    return render_template("coupon.html", title="Coupon") # RENDERS THE COUPON PAGE







