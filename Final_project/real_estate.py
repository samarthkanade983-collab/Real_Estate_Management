import hmac

from flask import Flask, jsonify, redirect, render_template, request, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text, func, desc
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import uuid
import re
import random

# ------------------ APP CONFIG ------------------ #
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ DATABASE (MySQL) ------------------ #
password = quote_plus("Estate@123!")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://estate_user:{password}@localhost/real_estate_db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ------------------ FILE UPLOAD SETTINGS ------------------ #
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ MODELS ------------------ #
#----------User Model----------#
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    name = db.Column(db.String(100))
    number = db.Column(db.String(20))
    address = db.Column(db.String(300))
    gender = db.Column(db.String(10))
    profile_img = db.Column(db.String(300))

    role = db.Column(db.String(50), nullable=False, default="user")  
    # user / admin

    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    properties = db.relationship(
    "Property",
    foreign_keys="Property.user_id",
    backref="owner",
    lazy=True
)
    wishlist_items = db.relationship("Wishlist", backref="user", lazy=True)
    scheduled_visits = db.relationship("PropertyVisit", backref="scheduled_user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"
    
#-------Agent Model------#    
class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(256), nullable=False)

    department = db.Column(db.String(50), nullable=False)
    # broker / sales

    email_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default="pending")
    # pending / approved / rejected

    total_deals_closed = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    agent_profile_img = db.Column(db.String(300))
    agent_gender = db.Column(db.String(20))

    visits = db.relationship("PropertyVisit", backref="agent", lazy=True)
    broker_transactions = db.relationship(
        "Transaction",
        foreign_keys="Transaction.broker_id",
        backref="broker",
        lazy=True
    )
    sales_transactions = db.relationship(
        "Transaction",
        foreign_keys="Transaction.sales_staff_id",
        backref="sales_staff",
        lazy=True
    )

    def __repr__(self):
        return f"<Agent {self.email}>"
    
#-------Property Model-------#
class Property(db.Model):
    __tablename__ = "property"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    registration_id = db.Column(db.String(100), unique=True, nullable=False)
    owner_phone = db.Column(db.String(15), nullable=False)
    owner_email = db.Column(db.String(150), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50))
    rental_category = db.Column(db.String(100))
    sale_category = db.Column(db.String(100))
    rental_available_from = db.Column(db.Date)
    sale_available_from = db.Column(db.Date)
    thumbnail = db.Column(db.String(300), nullable=False)
    is_ongoing = db.Column(db.Boolean, default=False)
    show_in_carousel = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="pending")  # pending / agent_verified / approved / rejected / sold / under_offer
    verified_by = db.Column(db.String(150), db.ForeignKey("agents.name"))
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    images = db.relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", backref="property", lazy=True)
    visits = db.relationship("PropertyVisit", backref="property_obj", lazy=True)

    def __repr__(self):
        return f"<Property {self.title}>"

#-------Property Images Model-------#
class PropertyImage(db.Model):
    __tablename__ = "property_images"

    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(300), nullable=False)

    property_id = db.Column(
        db.Integer,
        db.ForeignKey("property.id"),
        nullable=False
    )

    property = db.relationship("Property", back_populates="images")

    def __repr__(self):
        return f"<PropertyImage {self.image}>"
    
#-------Wishlist Model-------#
class Wishlist(db.Model):
    __tablename__ = "wishlist"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)

    property = db.relationship("Property", backref="wishlisted_by")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'property_id', name='unique_wishlist_item'),
    )

    def __repr__(self):
        return f"<Wishlist user:{self.user_id} property:{self.property_id}>"

#-------Property Visit Model-------#
class PropertyVisit(db.Model):
    __tablename__ = "property_visit"

    id = db.Column(db.Integer, primary_key=True)

    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    scheduled_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))

    visit_date = db.Column(db.Date, nullable=False)
    visit_time = db.Column(db.Time, nullable=False)

    status = db.Column(db.String(20), default="scheduled")
    # scheduled / completed / cancelled

    remarks = db.Column(db.Text)

    property = db.relationship("Property", backref="property_visits")
    def __repr__(self):
        return f"<Visit Property:{self.property_id}>"
    
#-------Transaction Model-------#
class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)

    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)

    buyer_name = db.Column(db.String(150), nullable=False)
    buyer_email = db.Column(db.String(150), nullable=False)
    buyer_phone = db.Column(db.String(20), nullable=False)

    broker_id = db.Column(db.Integer, db.ForeignKey("agents.id"))
    sales_staff_id = db.Column(db.Integer, db.ForeignKey("agents.id"))

    final_price = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float)

    status = db.Column(db.String(20), default="initiated")
    # initiated / completed / cancelled

    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction Property:{self.property_id}>"
    
#--------Otp Model-------#
class EmailOTP(db.Model):
    __tablename__ = "email_otps"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(150), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)

    purpose = db.Column(db.String(50), nullable=False)
    # register_user / register_agent / reset_password

    is_verified = db.Column(db.Boolean, default=False)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmailOTP {self.email} - {self.purpose}>"


# ------------------ DECORATORS ------------------ #
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            session_role = session.get("role")

            # Not logged in at all
            if not session_role:
                flash("Please login first.", "danger")
                return redirect(url_for("home"))

            # Role-based restriction
            if role:
                if isinstance(role, list):
                    if session_role not in role:
                        flash("Access denied.", "danger")
                        return redirect(url_for("home"))
                else:
                    if session_role != role:
                        flash("Access denied.", "danger")
                        return redirect(url_for("home"))

            return f(*args, **kwargs)

        return wrapped
    return decorator


# ------------------ ROUTES ------------------ #
@app.route("/")
def home():
    properties = Property.query.filter_by(status="approved").all()

    carousel_projects = Property.query.filter_by(
        show_in_carousel=True
    ).all()

    ongoing_projects = Property.query.filter_by(
        is_ongoing=True
    ).all()

    return render_template(
        "user/home.html",
        properties=properties,
        carousel_projects=carousel_projects,
        ongoing_projects=ongoing_projects
    )

@app.route("/favicon.ico")
def favicon():
    return "", 204

MAX_OTP_ATTEMPTS = 5  

# ------------------ USER SIGN-UP ------------------ #
@app.route("/user/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")
        address = request.form.get("address")
        gender = request.form.get("gender")
        number = request.form.get("number")
        image_file = request.files.get("profile_img")

        if not all([email, password, name, address, gender, number]):
            flash("All fields are required", "danger")
            return redirect(url_for("sign_up"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect(url_for("sign_up"))

        # Handle profile image
        filename = None
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
                image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                flash("Invalid image format", "danger")
                return redirect(url_for("sign_up"))

        try:
            # Create user
            user = User(
                email=email,
                password=generate_password_hash(password),
                name=name,
                address=address,
                gender=gender,
                number=number,
                profile_img=filename,
                role="user",
                email_verified=True,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()

            # Generate OTP
            otp = generate_otp()
            otp_entry = EmailOTP(
                email=email,
                otp_code=otp,
                purpose="register_user",
                expires_at=datetime.utcnow() + timedelta(minutes=2),
                is_used=False
            )
            db.session.add(otp_entry)
            db.session.commit()

            send_email_otp(email, otp)
            flash("OTP sent to your email. Please verify.", "info")
            return redirect(url_for("verify_otp", email=email, purpose="register_user"))
        except Exception as e:
            db.session.rollback()
            flash("Error creating account. Try again.", "danger")
            return redirect(url_for("sign_up"))

    return render_template("user/sign-up.html")


# Send OTP for registration
@app.route("/send_otp", methods=["GET"])
def send_otp_route():
    email = request.args.get("email")
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    otp = generate_otp()

    EmailOTP.query.filter_by(
    email=email,
    purpose="register_user",
    is_used=False
    ).delete()
    
    otp_entry = EmailOTP(
        email=email,
        otp_code=otp,
        purpose="register_user",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        is_used=False
    )
    db.session.add(otp_entry)
    db.session.commit()

    send_email_otp(email, otp)
    return jsonify({"status": "success", "message": "OTP sent to email."})


# Verify OTP via AJAX
@app.route("/verify_otp_ajax", methods=["POST"])
def verify_otp_ajax():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")
    purpose = "register_user"

    if not email or not otp:
        return jsonify({"status": "error", "message": "Email and OTP are required."})

    otp_attempts = session.get(f"otp_attempts_{email}", 0)
    if otp_attempts >= MAX_OTP_ATTEMPTS:
        return jsonify({"status": "error", "message": "Too many OTP attempts. Please request a new OTP."})

    otp_entry = EmailOTP.query.filter_by(
        email=email,
        purpose=purpose,
        is_used=False
    ).order_by(EmailOTP.id.desc()).first()

    if not otp_entry:
        return jsonify({"status": "error", "message": "No OTP found. Please request a new one."})

    if datetime.utcnow() > otp_entry.expires_at:
        return jsonify({"status": "error", "message": "OTP expired. Please request a new one."})

    if not hmac.compare_digest(otp_entry.otp_code, otp):
        session[f"otp_attempts_{email}"] = otp_attempts + 1
        return jsonify({
            "status": "error",
            "message": f"Invalid OTP. Attempts left: {MAX_OTP_ATTEMPTS - session[f'otp_attempts_{email}']}"
        })

    otp_entry.is_used = True
    db.session.commit()
    session.pop(f"otp_attempts_{email}", None)
    return jsonify({"status": "success", "message": "OTP verified successfully!"})


# Register user (after OTP verification)
@app.route("/register_user_ajax", methods=["POST"])
def register_user_ajax():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    address = data.get("address")
    gender = data.get("gender")
    number = data.get("number")

    if not all([email, password, name, address, gender, number]):
        return jsonify({"status": "error", "message": "All fields are required."})

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered."})

    try:
        user = User(
            email=email,
            password=generate_password_hash(password),
            name=name,
            address=address,
            gender=gender,
            number=number,
            role="user",
            email_verified=True,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Registration successful. Redirecting...", "redirect": url_for("sign_in")})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Error creating account. Try again."})

# ------------------ USER LOGIN ------------------ #
@app.route("/user/sign-in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email, role="user").first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials", "danger")
            return redirect(url_for("sign_in"))

        if not user.email_verified:
            flash("Please verify your email first.", "warning")
            return redirect(url_for("sign_in"))

        if not user.is_active:
            flash("Account not activated.", "warning")
            return redirect(url_for("sign_in"))

        # Clear session and set secure session variables
        session.clear()
        session["user_id"] = user.id
        session["role"] = "user"
        session["user_email"] = user.email

        return redirect(url_for("home"))

    return render_template("user/sign-in.html")


# ------------------ USER PROFILE ------------------ #
@app.route("/user/profile", methods=["GET", "POST"])
@login_required(role="user")
def profile():
    user = User.query.filter_by(email=session.get("user_email")).first()

    if request.method == "POST":
        user.name = request.form.get("name") or user.name
        user.address = request.form.get("address") or user.address
        user.gender = request.form.get("gender") or user.gender
        user.number = request.form.get("number") or user.number

        image_file = request.files.get("profile_img")
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
                image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                user.profile_img = filename
            else:
                return redirect(request.url)

        db.session.commit()

    return render_template("user/profile.html", user=user)

#------------------ VIEW ALL PROPERTIES ------------------ #
@app.route("/properties")
def all_properties():
    search = request.args.get("search")
    location = request.args.get("location")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    property_type = request.args.get("property_type")
    rental_category = request.args.get("rental_category")
    sale_category = request.args.get("sale_category")

    query = Property.query.filter_by(status="approved")

    if search:
        query = query.filter(Property.title.ilike(f"%{search}%"))

    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))

    if min_price:
        query = query.filter(Property.price >= int(min_price))

    if max_price:
        query = query.filter(Property.price <= int(max_price))
    
    if property_type:
        query = query.filter(Property.property_type == property_type)


    properties = query.order_by(Property.id.desc()).all()
    return render_template("user/properties.html", properties=properties)

#------------------ VIEW PROPERTY DETAILS ------------------ #
@app.route("/property/<int:property_id>")
def property_details(property_id):
    property = Property.query.get_or_404(property_id)
    if property.status != "approved":
        return redirect(url_for("all_properties"))

    return render_template("user/property_details.html", property=property)


# ------------------ UPLOAD PROPERTY ------------------ #
@app.route("/user/upload-property", methods=["GET", "POST"])
@login_required(role="user")
def upload_property():

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price")
        location = request.form.get("location")
        registration_id = request.form.get("registration_id")
        owner_phone = request.form.get("owner_phone")
        owner_email = request.form.get("owner_email")
        otp = request.form.get("otp")   
        owner_name = request.form.get("owner_name")
        property_type = request.form.get("property_type")
        rental_category = request.form.get("rental_category")
        sale_category = request.form.get("sale_category")
        rental_available_from = request.form.get("rental_available_from")
        sale_available_from = request.form.get("sale_available_from")
        

        thumbnail = request.files.get("thumbnail")
        images = request.files.getlist("images")

        #  Validate required fields
        if not all([title, description, price, location, thumbnail, registration_id, owner_phone, owner_email, owner_name, property_type]):
            flash("All fields including thumbnail are required", "danger")
            return redirect(request.url)

        if not images or images[0].filename == "":
            flash("At least one gallery image is required", "danger")
            return redirect(request.url)

        if not re.match(r"^REG-\d{6}$", registration_id):
            flash("Invalid Registration ID format. Use REG-123456", "danger")
            return redirect(request.url)

        if not allowed_file(thumbnail.filename):
            flash("Invalid thumbnail format", "danger")
            return redirect(request.url)
        otp_entry = EmailOTP.query.filter_by(
            email=owner_email,
            purpose="property_verification",
            is_used=False
        ).order_by(EmailOTP.id.desc()).first()

        if not otp_entry:
            flash("No OTP request found. Please request OTP first.", "danger")
            return redirect(request.url)

        if datetime.utcnow() > otp_entry.expires_at:
            flash("OTP expired. Please request a new one.", "danger")
            return redirect(request.url)

        if otp_entry.otp_code != otp:
            flash("Invalid OTP.", "danger")
            return redirect(request.url)

        # Mark OTP as used
        otp_entry.is_used = True

        #  Check duplicate registration ID
        existing = Property.query.filter_by(registration_id=registration_id).first()
        if existing:
            flash("This registration ID already exists!", "danger")
            return redirect(url_for("upload_property"))

        user = User.query.filter_by(email=session["user_email"]).first()

        #  Save thumbnail
        thumb_name = f"{uuid.uuid4().hex}_{secure_filename(thumbnail.filename)}"
        thumbnail.save(os.path.join(app.config["UPLOAD_FOLDER"], thumb_name))

        #  Convert dates safely
        try:
            rental_date = datetime.strptime(rental_available_from, "%Y-%m-%d") if rental_available_from else None
            sale_date = datetime.strptime(sale_available_from, "%Y-%m-%d") if sale_available_from else None
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(request.url)

        prop = Property(
            title=title,
            description=description,
            price=float(price),
            location=location,
            registration_id=registration_id,
            owner_phone=owner_phone,
            owner_email=owner_email,
            otp=otp,
            owner_name = owner_name,
            thumbnail=thumb_name,
            user_id=user.id,
            status="pending",
            property_type=property_type,
            rental_category=rental_category,
            sale_category=sale_category,
            rental_available_from=rental_date,
            sale_available_from=sale_date
        )

        db.session.add(prop)
        db.session.commit()

        for img in images:
            if img and allowed_file(img.filename):
                img_name = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                img.save(os.path.join(app.config["UPLOAD_FOLDER"], img_name))

                db.session.add(PropertyImage(
                    property_id=prop.id,
                    image=img_name
                ))

        db.session.commit()

    
        session.pop("phone_verified", None)
        session.pop("phone_otp", None)
        session.pop("otp_expiry", None)
        session.pop("otp_attempts", None)

        flash("Property uploaded successfully. Pending admin approval.", "success")
        return redirect(url_for("all_properties"))

    return render_template("user/upload-property.html")

@app.route("/user/my-properties")
@login_required(role="user")
def my_properties():
    user_id = session.get("user_id")

    properties = Property.query.filter_by(user_id=user_id).all()

    return render_template("user/my_properties.html", properties=properties)

#------------------ OTP GENERATION ------------------ #
def generate_otp():
    return str(random.randint(100000, 999999))

def send_email_otp(receiver_email, otp):
    sender_email = "reaestateportal11@gmail.com"
    app_password = "iqhwvetiwdugjcjr"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Estate App - OTP Verification"

    body = f"""
Hello,

Your OTP for phone verification is: {otp}

This OTP is valid for 5 minutes.
Do not share this with anyone.

Regards,
Estate App Team
"""

    message.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)
    server.sendmail(sender_email, receiver_email, message.as_string())
    server.quit()

@app.route("/send-otp-property", methods=["POST"])
@login_required(role="user")
def send_otp_property():
    data = request.get_json()
    email = data.get("email")

    if not email or "@" not in email:
        return {"success": False, "message": "Valid email required."}

    # Generate OTP
    otp = generate_otp()

    # Save OTP in DB
    otp_entry = EmailOTP(
        email=email,
        otp_code=otp,
        purpose="property_verification",
        is_used=False,
        is_verified=False,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )

    db.session.add(otp_entry)
    db.session.commit()

    # Send OTP via email
    send_email_otp(email, otp)

    return {"success": True, "message": "OTP sent successfully."}


#------------------- VERIFY OTP ------------------ #
@app.route("/verify-property-otp", methods=["POST"])
@login_required(role="user")
def verify_property_otp():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return {"success": False, "message": "Email and OTP are required."}

    # Find latest unused OTP for this email
    otp_entry = EmailOTP.query.filter_by(
        email=email,
        purpose="property_verification",
        is_used=False
    ).order_by(EmailOTP.id.desc()).first()

    if not otp_entry:
        return {"success": False, "message": "No OTP request found. Please request OTP first."}

    # Check expiration
    if datetime.utcnow() > otp_entry.expires_at:
        return {"success": False, "message": "OTP expired. Please request a new one."}

    # Check OTP match
    if otp_entry.otp_code != otp:
        return {"success": False, "message": "Invalid OTP."}

    # Mark OTP as used
    otp_entry.is_used = True
    otp_entry.is_verified = True
    db.session.commit()

    return {"success": True, "message": "OTP verified successfully."}

#------------- Add to wishlist --------------#
@app.route("/wishlist")
@login_required(role="user")
def view_wishlist():
    user = User.query.filter_by(email=session.get("user_email")).first()
    wishlist_properties = [item.property for item in user.wishlist_items]
    return render_template("user/wishlist.html", properties=wishlist_properties)

@app.route("/wishlist/add/<int:property_id>", methods=["POST"])
@login_required(role="user")
def add_to_wishlist(property_id):
    user = User.query.filter_by(email=session.get("user_email")).first()
    prop = Property.query.get_or_404(property_id)

    # Check if already in wishlist
    existing = Wishlist.query.filter_by(user_id=user.id, property_id=prop.id).first()
    if existing:
        flash("Property already in wishlist", "info")
    else:
        db.session.add(Wishlist(user_id=user.id, property_id=prop.id))
        db.session.commit()
        flash("Property added to wishlist", "success")

    return redirect(request.referrer or url_for("all_properties"))


# Remove from wishlist
@app.route("/wishlist/remove/<int:property_id>", methods=["POST"])
@login_required(role="user")
def remove_from_wishlist(property_id):
    user = User.query.filter_by(email=session.get("user_email")).first()
    wishlist_item = Wishlist.query.filter_by(user_id=user.id, property_id=property_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash("Property removed from wishlist", "success")
    return redirect(request.referrer or url_for("all_properties"))


# ------------------ ADMIN  ------------------ # 
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("admin_id")
        password = request.form.get("password")

        admin = User.query.filter_by(email=email, role="admin").first()

        if admin and check_password_hash(admin.password, password):
            session["user_id"] = admin.id   # FIXED
            session["role"] = "admin"
            session["user_email"] = admin.email
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials", "danger")
        return redirect(url_for("admin_login"))

    return render_template("admin/login.html")


@app.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():

    # USERS & AGENTS
    total_users = User.query.filter_by(role="user").count()
    total_agents = Agent.query.count()

    # PROPERTY STATS
    total_properties = Property.query.filter(
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).count()

    ongoing_properties = Property.query.filter(
        Property.is_ongoing == True,
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).count()


    pending_verification = Property.query.filter(
        Property.status == "pending",
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).count()

    pending_properties = Property.query.filter(
        Property.status == "pending",
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).count()

    # DEAL STATS
    total_completed_deals = Transaction.query.filter_by(
        status="completed"
    ).count()

    total_active_deals = Transaction.query.filter(
        Transaction.status.in_(["initiated", "under_process"])
    ).count()

    # FINANCIAL STATS
    total_revenue = db.session.query(
        func.sum(Transaction.final_price)
    ).filter(
        Transaction.status == "completed"
    ).scalar() or 0

    total_commission = db.session.query(
        func.sum(Transaction.commission_amount)
    ).filter(
        Transaction.status == "completed"
    ).scalar() or 0

    # TOP BROKER
    deal_count = func.count(Transaction.id).label("deal_count")

    top_broker = db.session.query(
        Agent.name,
        deal_count
    ).join(
        Transaction, Transaction.broker_id == Agent.id
    ).filter(
        Transaction.status == "completed"
    ).group_by(
        Agent.id
    ).order_by(
        desc(deal_count)
    ).first()

    # TOP SALES AGENT
    top_sales = db.session.query(
        Agent.name,
        func.count(Transaction.id).label("deal_count")
    ).join(
        Transaction, Transaction.sales_staff_id == Agent.id
    ).filter(
        Transaction.status == "completed"
    ).group_by(
        Agent.id
    ).order_by(
        desc(func.count(Transaction.id))
    ).first()

    # RECENT DEALS
    recent_deals = Transaction.query.order_by(
        Transaction.transaction_date.desc()
    ).limit(5).all()

    # RECENT PROPERTIES
    recent_properties = Property.query.filter(
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).order_by(
        Property.id.desc()
    ).limit(5).all()

    # ALL PROPERTIES (excluding sold/rented)
    all_properties = Property.query.filter(
        Property.status.notin_(["sold", "rented"]),
        (Property.is_deleted == False) | (Property.is_deleted == None)
    ).order_by(
        Property.id.desc()
    ).all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_agents=total_agents,
        total_properties=total_properties,
        ongoing_properties=ongoing_properties,
        pending_properties=pending_properties,
        pending_verification=pending_verification,
        total_completed_deals=total_completed_deals,
        total_active_deals=total_active_deals,
        total_revenue=total_revenue,
        total_commission=total_commission,
        top_broker=top_broker,
        top_sales=top_sales,
        recent_deals=recent_deals,
        recent_properties=recent_properties,
        properties=all_properties
    )

@app.route("/admin/toggle-ongoing/<int:property_id>", methods=["POST"])
@login_required(role="admin")
def toggle_ongoing(property_id):
    prop = Property.query.get_or_404(property_id)
    prop.is_ongoing = not prop.is_ongoing
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/toggle-carousel/<int:property_id>", methods=["POST"])
@login_required(role="admin")
def toggle_carousel(property_id):

    prop = Property.query.get_or_404(property_id)
    prop.show_in_carousel = not prop.show_in_carousel

    db.session.commit()
    return redirect(request.referrer)

@app.route("/admin/manage-properties")
@login_required(role="admin")
def manage_properties():
    properties = Property.query.filter(Property.status.in_(["verified", "approved"])) \
                               .order_by(Property.id.desc()) \
                               .all()
    return render_template("admin/manage-properties.html", properties=properties)


# ------------------ ADMIN APPROVE PROPERTY ------------------ #
@app.route("/admin/approve-property/<int:property_id>")
@login_required(role="admin")
def approve_property(property_id):

    prop = Property.query.get_or_404(property_id)

    if prop.status != "verified":
        flash("Property must be verified by agent first!", "danger")
        return redirect(url_for("manage_properties"))

    prop.status = "approved"
    prop.approved_by = session.get("user_id")

    db.session.commit()

    flash("Property approved successfully", "success")
    return redirect(url_for("manage_properties"))


# ------------------ ADMIN DELETE PROPERTY ------------------ #
@app.route("/admin/delete-property/<int:property_id>", methods=["POST"])
@login_required(role="admin")
def admin_delete_property(property_id):
    prop = Property.query.get_or_404(property_id)

    # Delete all visits associated with this property
    PropertyVisit.query.filter_by(property_id=prop.id).delete()

    # Delete property images
    if prop.thumbnail:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], prop.thumbnail))
        except FileNotFoundError:
            pass

    db.session.delete(prop)
    db.session.commit()
    flash("Property deleted successfully!", "success")
    return redirect(url_for("manage_properties"))

#------------- Agents actions ---------#
@app.route("/admin/manage-agents")
@login_required(role="admin")
def manage_agents():
    agents = Agent.query.all()
    return render_template("admin/manage-agents.html", agents=agents)

@app.route("/admin/delete-agent/<int:agent_id>", methods=["POST"], endpoint="admin_delete_agent")
@login_required(role="admin")
def delete_agent(agent_id):

    agent = Agent.query.get_or_404(agent_id)

    # Prevent deleting agent with active deals
    active_deals = Transaction.query.filter(
        (Transaction.broker_id == agent.id) |
        (Transaction.sales_staff_id == agent.id),
        Transaction.status == "initiated"
    ).first()

    if active_deals:
        flash("Cannot delete agent with active deals.", "danger")
        return redirect(url_for("manage_agents"))

    # Remove agent from visits
    PropertyVisit.query.filter_by(agent_id=agent.id).update({"agent_id": None})

    # Delete profile image safely
    if agent.agent_profile_img:
        profile_img_path = os.path.join(app.config["UPLOAD_FOLDER"], agent.agent_profile_img)
        try:
            os.remove(profile_img_path)
        except FileNotFoundError:
            pass

    db.session.delete(agent)
    db.session.commit()

    flash("Agent deleted successfully!", "success")
    return redirect(url_for("manage_agents"))

@app.route("/admin/approve-agent/<int:agent_id>")
@login_required(role="admin")
def approve_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.status = "approved"
    db.session.commit()
    flash("Agent approved successfully", "success")
    return redirect(url_for("manage_agents"))


@app.route("/admin/reject-agent/<int:agent_id>")
@login_required(role="admin")
def reject_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.status = "rejected"
    db.session.commit()
    flash("Agent rejected", "danger")
    return redirect(url_for("manage_agents"))

@app.route("/admin/activate-agent/<int:agent_id>")
@login_required(role="admin")
def activate_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.status = "approved"
    db.session.commit()
    flash("Agent activated successfully", "success")
    return redirect(url_for("manage_agents"))

@app.route("/admin/suspend-agent/<int:agent_id>")
@login_required(role="admin")
def suspend_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.status = "suspended"
    db.session.commit()
    flash("Agent suspended successfully", "warning")
    return redirect(url_for("manage_agents"))

@app.route("/admin/deals")
@login_required(role="admin")
def admin_deals():

    deals = Transaction.query.order_by(Transaction.transaction_date.desc()).all()

    total_revenue = sum(d.final_price for d in deals if d.status == "completed")
    total_commission = sum(d.commission_amount for d in deals if d.status == "completed")

    return render_template(
        "admin/deals.html",
        deals=deals,
        total_revenue=total_revenue,
        total_commission=total_commission
    )


@app.route("/admin/view-agent/<int:agent_id>")
@login_required(role="admin")
def view_agent_profile(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    return render_template("admin/view_agent_profile.html", agent=agent)

@app.route("/admin/visits")
@login_required(role="admin")
def view_visits():
    visits = PropertyVisit.query.order_by(PropertyVisit.visit_date.desc()).all()
    return render_template("admin/visits.html", visits=visits)


#-------------------Agents------------------#

@app.route('/agents/login', methods=['GET', 'POST'])
def agent_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        agent = Agent.query.filter_by(email=email).first()

        if not agent or not check_password_hash(agent.password, password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for("agent_login"))

        if not agent.email_verified:
            flash("Please verify your email first.", "warning")
            return redirect(url_for("agent_login"))

        if agent.status != "approved":
            flash("Your account is not approved by admin yet.", "warning")
            return redirect(url_for("agent_login"))

        session['role'] = 'agent'
        session['agent_id'] = agent.id

        return redirect(url_for('agent_dashboard'))

    return render_template('agents/agent_login.html')

@app.route("/register_agent_ajax", methods=["POST"])
def register_agent_ajax():

    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    department = request.form.get("department").capitalize()
    agent_gender = request.form.get("agent_gender")
    agent_profile_img = request.files.get("agent_profile_img")

    if not all([name, email, phone, password, department, agent_gender]):
        flash("All fields are required.", "danger")
        return redirect(request.referrer)

    if Agent.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
        return redirect(request.referrer)

    try:
        filename = None
        if agent_profile_img:
            filename = agent_profile_img.filename

        agent = Agent(
            name=name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            department=department,
            agent_gender=agent_gender,
            agent_profile_img=filename,
            status="pending",
            email_verified=True,
            is_active=False
        )

        db.session.add(agent)
        db.session.commit()

        flash("Agent registered successfully. Waiting for admin approval.", "success")
        return redirect(url_for("agent_login"))

    except Exception as e:
        db.session.rollback()
        flash("Error creating agent account.", "danger")
        return redirect(request.referrer)

@app.route('/agents/signup', methods=['GET', 'POST'])
def agent_signup():
    return render_template('agents/agent_signup.html')


@app.route('/agents/dashboard')
def agent_dashboard():
    if session.get('role') != 'agent':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    agent = Agent.query.get(session.get('agent_id'))

    pending_properties = Property.query.filter_by(status = "pending").all()
    pending_count = len(pending_properties)

    verified_count = Property.query.filter_by(status = "approved").count()
    total_deal_value = db.session.query(
    func.sum(Transaction.final_price)
    ).filter(
    Transaction.status == "completed"
    ).scalar() or 0

    visits = PropertyVisit.query.filter_by(
        agent_id=agent.id,
        status="scheduled"
    ).all()
    visit_count = len(visits)
    active_deals = Transaction.query.filter(
        (Transaction.broker_id == agent.id) | (Transaction.sales_staff_id == agent.id),
        Transaction.status.in_(["initiated", "under_process"])
    ).count()
    
    completed_deals = Transaction.query.filter(
        (Transaction.broker_id == agent.id) | (Transaction.sales_staff_id == agent.id),
        Transaction.status == "completed"
    ).count()

    return render_template(
        'agents/dashboard.html',
        agent=agent,
        pending_properties=pending_properties,
        pending_count=pending_count,
        verified_count=verified_count,
        visits=visits,
        total_deal_value=total_deal_value,
        visit_count=visit_count,
        active_deals=active_deals,
        completed_deals=completed_deals
    )

@app.route("/agents/properties")
@login_required(role="agent")
def agent_properties():

    properties = Property.query.all()

    return render_template(
        "agents/properties.html",
        properties=properties
    )

@app.route('/agents/view_property/<int:property_id>')
@login_required(role="agent")
def agent_view_property(property_id):

    prop = Property.query.get_or_404(property_id)

    agent = Agent.query.get(session.get("agent_id"))

    return render_template(
        "agents/view_property.html",
        property=prop,
        agent=agent
    )
    
@app.route('/agents/verify/<int:property_id>')
@login_required(role="agent")
def agent_verify_property(property_id):

    agent = Agent.query.get(session.get("agent_id"))

    if agent.department != "broker":
        flash("Only brokers can verify properties.", "danger")
        return redirect(url_for("agent_dashboard"))

    prop = Property.query.get_or_404(property_id)

    if prop.status != "pending":
        flash("Property already processed!", "warning")
        return redirect(url_for("agent_dashboard"))

    prop.status = "approved"
    prop.approved_by = session.get("user_id")
    db.session.commit()

    flash("Property verified successfully!", "success")
    return redirect(url_for("agent_dashboard"))


# ---------------- CREATE DEAL ---------------- #
@app.route("/agents/create_deals/<int:property_id>", methods=["GET", "POST"])
@login_required(role="agent")
def create_deals(property_id):

    agent = Agent.query.get_or_404(session.get("agent_id"))

    # Allow only Sales department
    if agent.department.lower() != "sales":
        return redirect(url_for("agent_dashboard"))

    prop = Property.query.get_or_404(property_id)

    if prop.status != "approved":
        return redirect(url_for("agent_dashboard"))

    # Broker who verified property
    broker = Agent.query.get(prop.verified_by)

    if request.method == "POST":

        buyer_name = request.form.get("buyer_name")
        buyer_email = request.form.get("buyer_email")
        buyer_phone = request.form.get("buyer_phone")
        final_price = request.form.get("final_price")

        if not final_price:
            flash("Final price is required.", "danger")
            return redirect(request.url)

        final_price = float(final_price)

        COMMISSION_RATE = 0.02
        commission = final_price * COMMISSION_RATE

        transaction = Transaction(
            property_id=prop.id,
            buyer_name=buyer_name,
            buyer_email=buyer_email,
            buyer_phone=buyer_phone,
            broker_id=broker.id if broker else None,
            sales_staff_id=agent.id,
            final_price=final_price,
            commission_amount=commission,
            status="initiated"
        )

        prop.status = "under_offer"

        db.session.add(transaction)
        db.session.commit()

        return redirect(url_for("agent_dashboard"))

    return render_template(
        "agents/create_deals.html",
        property=prop,
        broker=broker
    )


# ---------------- COMPLETE DEAL ---------------- #
@app.route("/agents/complete-deal/<int:transaction_id>", methods=["POST"])
@login_required(role="agent")
def complete_deal(transaction_id):

    agent = Agent.query.get_or_404(session.get("agent_id"))

    if agent.department.lower() != "sales":
        return redirect(url_for("agent_dashboard"))

    transaction = Transaction.query.get_or_404(transaction_id)
    property_obj = Property.query.get_or_404(transaction.property_id)

    # Prevent completing another agent's deal
    if transaction.sales_staff_id != agent.id:
        flash("You cannot complete another agent's deal.", "danger")
        return redirect(url_for("agent_dashboard"))

    if transaction.status == "completed":
        return redirect(url_for("agent_dashboard"))

    transaction.status = "completed"

    # Set property status
    if property_obj.sale_category:
        property_obj.status = "sold"
    elif property_obj.rental_category:
        property_obj.status = "rented"

    broker = Agent.query.get(transaction.broker_id)
    if broker:
        broker.total_deals_closed = (broker.total_deals_closed or 0) + 1

    db.session.commit()

    return redirect(url_for("agent_dashboard"))


# ---------------- CANCEL DEAL ---------------- #
@app.route("/agents/cancel-deal/<int:transaction_id>", methods=["POST"])
@login_required(role="agent")
def cancel_deal(transaction_id):

    agent = Agent.query.get_or_404(session.get("agent_id"))

    if agent.department.lower() != "sales":
        return redirect(url_for("agent_dashboard"))

    transaction = Transaction.query.get_or_404(transaction_id)
    property_obj = Property.query.get_or_404(transaction.property_id)

    # Prevent cancelling other agent's deal
    if transaction.sales_staff_id != agent.id:
        flash("You cannot cancel another agent's deal.", "danger")
        return redirect(url_for("agent_dashboard"))

    if transaction.status == "completed":
        flash("Completed deals cannot be cancelled.", "danger")
        return redirect(url_for("agent_dashboard"))

    transaction.status = "cancelled"
    property_obj.status = "approved"

    db.session.commit()

    flash("Deal cancelled.", "warning")
    return redirect(url_for("agent_dashboard"))

@app.route("/agents/my-deals")
@login_required(role="agent")
def my_deals():

    agent_id = session.get("agent_id")

    deals = Transaction.query.filter_by(
        sales_staff_id=agent_id
    ).order_by(Transaction.transaction_date.desc()).all()

    return render_template(
        "agents/my_deals.html",
        deals=deals
    )

#------------Agent Profile ---------#
@app.route('/agents/profile', methods=['GET', 'POST'])
def agent_profile():
    if session.get('role') != 'agent':
        return redirect(url_for('home'))

    agent = Agent.query.get(session.get('agent_id'))
    if not agent:
        flash('Agent not found', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        agent_gender =  request.form.get('agent_gender')
        agent_profile_img = request.files.get('agent_profile_img')

        agent.name = name
        agent.email = email
        agent.phone = phone
        agent.agent_gender = agent_gender
        if agent_profile_img:
            filename = secure_filename(agent_profile_img.filename)
            agent_profile_img.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            agent.agent_profile_img = filename

        db.session.commit()

    return render_template('agents/agent_profile.html', agent=agent)


#----------------Schedule Visit------------------#

@app.route("/user/schedule-visit/<int:property_id>", methods=["GET", "POST"])
@login_required(role="user")
def user_schedule_visit(property_id):
    property = Property.query.get_or_404(property_id)

    if request.method == "POST":

        visit_date_obj = datetime.strptime(
            request.form.get("visit_date"), "%Y-%m-%d"
        ).date()

        visit_time_obj = datetime.strptime(
            request.form.get("visit_time"), "%H:%M"
        ).time()

        # Get approved agents
        agents = Agent.query.filter_by(status="approved").all()

        if not agents:
            flash("No agents available right now.", "danger")
            return redirect(url_for("user_schedule_visit", property_id=property_id))

        random.shuffle(agents)

        assigned_agent = None

        for agent in agents:
            conflict = PropertyVisit.query.filter_by(
                agent_id=agent.id,
                visit_date=visit_date_obj,
                visit_time=visit_time_obj,
                status="scheduled"
            ).first()

            if not conflict:
                assigned_agent = agent
                break

        if not assigned_agent:
            flash("No agents available at this time. Try another slot.", "danger")
            return redirect(url_for("user_schedule_visit", property_id=property_id))

        new_visit = PropertyVisit(
            property_id=property.id,
            scheduled_by=session.get("user_id"),
            role="user",
            agent_id=assigned_agent.id,
            visit_date=visit_date_obj,
            visit_time=visit_time_obj,
            status="scheduled"
        )

        db.session.add(new_visit)
        db.session.commit()

        flash(f"Visit scheduled! Assigned agent: {assigned_agent.name}", "success")
        return redirect(url_for("my_visits"))

    return render_template("schedule_visit.html", property=property)

@app.route("/agent/schedule-visit/<int:property_id>", methods=["GET", "POST"])
@login_required(role="agent")
def agent_schedule_visit(property_id):

    property = Property.query.get_or_404(property_id)

    if request.method == "POST":

        visit_date_obj = datetime.strptime(
            request.form.get("visit_date"), "%Y-%m-%d"
        ).date()

        visit_time_obj = datetime.strptime(
            request.form.get("visit_time"), "%H:%M"
        ).time()

        agent_id = session.get("agent_id") 

        if not agent_id:
            flash("Session expired. Please login again.", "danger")
            return redirect(url_for("agent_login"))

        conflict = PropertyVisit.query.filter_by(
            agent_id=agent_id,
            visit_date=visit_date_obj,
            visit_time=visit_time_obj,
            status="scheduled"
        ).first()

        if conflict:
            flash("You already have a visit at this time.", "danger")
            return redirect(url_for("agent_schedule_visit", property_id=property_id))

        new_visit = PropertyVisit(
            property_id=property.id,
            scheduled_by=agent_id,
            role="agent",
            agent_id=agent_id,
            visit_date=visit_date_obj,
            visit_time=visit_time_obj,
            status="scheduled"
        )

        db.session.add(new_visit)
        db.session.commit()

        flash("Visit scheduled successfully!", "success")
        return redirect(url_for("agent_dashboard"))
    return render_template("schedule_visit.html", property=property)


@app.route("/my-visits")
@login_required()
def my_visits():
    role = session.get("role")

    if role == "user":
        visits = PropertyVisit.query.filter(
            PropertyVisit.scheduled_by == session.get("user_id"),
            PropertyVisit.status.in_(["scheduled", "cancelled"])
        ).all()
    elif role == "agent":
        visits = PropertyVisit.query.filter(
            PropertyVisit.agent_id == session.get("agent_id"),
            PropertyVisit.status.in_(["scheduled", "cancelled"])
        ).all()
    else:
        return redirect(url_for("home"))

    return render_template("my_visits.html", visits=visits)


@app.route("/reschedule-visit/<int:visit_id>", methods=["GET", "POST"])
@login_required(role="user")
def reschedule_visit(visit_id):
    visit = PropertyVisit.query.get_or_404(visit_id)

    if visit.scheduled_by != session.get("user_id"):
        flash("You are not authorized to reschedule this visit.", "danger")
        return redirect(url_for("my_visits"))

    if request.method == "POST":
        new_date = request.form.get("visit_date")
        new_time = request.form.get("visit_time")

        new_visit_date_obj = datetime.strptime(new_date, "%Y-%m-%d").date()
        new_visit_time_obj = datetime.strptime(new_time, "%H:%M").time()

        # Check for agent conflict
        conflict = PropertyVisit.query.filter(
            PropertyVisit.agent_id == visit.agent_id,
            PropertyVisit.visit_date == new_visit_date_obj,
            PropertyVisit.visit_time == new_visit_time_obj,
            PropertyVisit.status == "scheduled",
            PropertyVisit.id != visit.id
        ).first()

        if conflict:
            flash("Agent is not available at the new time. Please choose another slot.", "danger")
            return redirect(url_for("reschedule_visit", visit_id=visit_id))

        # Update visit
        visit.visit_date = new_visit_date_obj
        visit.visit_time = new_visit_time_obj
        visit.status = "scheduled"
        db.session.commit()

        flash("Visit rescheduled successfully!", "success")
        return redirect(url_for("my_visits"))

    return render_template("reschedule_visit.html", visit=visit)

@app.route("/visit/done/<int:visit_id>", methods=["POST"])
@login_required(role="agent")
def mark_visit_done(visit_id):
    visit = PropertyVisit.query.get_or_404(visit_id)
    visit.status = "done"   # or "completed"
    db.session.commit()
    flash("Visit marked as done", "success")
    return redirect(url_for("my_visits"))


@app.route("/cancel-visit/<int:visit_id>", methods=["POST"])
@login_required()
def cancel_visit(visit_id):

    visit = PropertyVisit.query.get_or_404(visit_id)

    # Ownership check
    if visit.scheduled_by != session.get("user_id") or visit.role != session.get("role"):
        flash("Unauthorized action", "danger")
        return redirect(url_for("home"))

    visit.status = "cancelled"
    db.session.commit()

    flash("Visit cancelled successfully", "success")
    return redirect(url_for("my_visits"))

#------------------- About --------------------#
@app.route("/about")
def about():
    return render_template("about.html")

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ------------------ LOGOUT ------------------ #
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("home"))



# ------------------ START APP ------------------ #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(email="admin@estate.com").first():
            admin = User(
                email="admin@estate.com",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True, port=8000)