from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_caching import Cache

db = SQLAlchemy()
cache = Cache()

# ---------------------------------------------------------
# USER MODEL
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) 

    is_active = db.Column(db.Boolean, default=True)

    # FIX (bug #1): admin.py / staff.py read u.created_at for the "Joined" column.
    # That column never existed on this model, so those list endpoints crashed
    # with a 500 error. Added here.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Advanced User Demographics & Safety Data
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    emergency_contact = db.Column(db.String(50), nullable=True)
    medical_conditions = db.Column(db.Text, nullable=True)
    experience_level = db.Column(db.String(20), default='Beginner') # Beginner, Moderate, Expert
    
    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy=True)
    staff_profile = db.relationship('StaffProfile', backref='user', uselist=False)
    
    # FIXED: We moved assigned_treks here because Trek.staff_id points to users.id!
    assigned_treks = db.relationship('Trek', backref='guide', lazy=True)

class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # FIX (bug #2): routes/staff.py created/read this as `contact_details`, which
    # didn't exist on this model (it only had `phone`) -> TypeError on staff
    # creation and AttributeError on staff listing. Renamed to match the
    # frontend field name/spec ("Contact Details").
    contact_details = db.Column(db.String(20), nullable=True)
    years_experience = db.Column(db.Integer, default=0)
    certifications = db.Column(db.String(200), nullable=True) # e.g. "Wilderness First Responder"

# ---------------------------------------------------------
# TREK MODEL (Upgraded)
# ---------------------------------------------------------
class Trek(db.Model):
    __tablename__ = 'trek'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    
    # Standard requirements
    difficulty = db.Column(db.String(50), nullable=False) 
    duration = db.Column(db.Integer, nullable=False) 
    available_slots = db.Column(db.Integer, nullable=False)
    
    # Points to users.id
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    status = db.Column(db.String(50), default='Pending') 
    
    # FIX (extra bug found while patching): these were declared as String, but
    # routes/trek.py always assigned real datetime objects to them
    # (datetime.strptime(...)). That "worked" only in the same request/session
    # because SQLAlchemy kept the Python object in memory; the moment the app
    # restarted and re-read the row from disk, SQLite/SQLAlchemy would hand
    # back a plain string, and every `.strftime(...)` call on it elsewhere
    # (trek.py, staff_ops.py, user_ops.py, jobs/tasks.py) would crash with
    # AttributeError. Declaring them as Date makes the round-trip correct.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Custom Extensions for Analytics & E-commerce
    base_price = db.Column(db.Float, default=0.0)
    max_altitude = db.Column(db.Integer, nullable=True) # Stored in meters
    difficulty_score = db.Column(db.Integer, default=50) # 1 to 100 scale for graphing
    
    # Relationships
    bookings = db.relationship('Booking', backref='trek', cascade="all, delete-orphan", lazy=True)
    reviews = db.relationship('TrekReview', backref='trek', cascade="all, delete-orphan", lazy=True)

# ---------------------------------------------------------
# BOOKING MODEL (Upgraded)
# ---------------------------------------------------------
class Booking(db.Model):
    __tablename__ = 'booking'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Booked') 
    payment_status = db.Column(db.String(50), default='Pending')

    # NEW: needed so cancellation/completion has a timestamp for history views
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Custom Extensions for Realism
    emergency_contact = db.Column(db.String(100), nullable=True)
    special_requirements = db.Column(db.String(255), nullable=True)

# ---------------------------------------------------------
# TREK REVIEW MODEL (New - For Analytics Dashboard)
# ---------------------------------------------------------
class TrekReview(db.Model):
    __tablename__ = 'trek_review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)