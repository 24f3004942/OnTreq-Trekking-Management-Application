from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ---------------------------------------------------------
# USER MODEL
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    staff_profile = db.relationship('StaffProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    bookings = db.relationship('Booking', backref='user', lazy=True)
    assigned_treks = db.relationship('Trek', backref='staff', lazy=True)
    reviews = db.relationship('TrekReview', backref='reviewer', lazy=True)

# ---------------------------------------------------------
# STAFF PROFILE MODEL
# ---------------------------------------------------------
class StaffProfile(db.Model):
    __tablename__ = 'staff_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact_details = db.Column(db.String(15), nullable=False)

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
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    status = db.Column(db.String(50), default='Pending') 
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Booked') 
    payment_status = db.Column(db.String(50), default='Pending')
    
    # Custom Extensions for Realism
    emergency_contact = db.Column(db.String(100), nullable=True)
    special_requirements = db.Column(db.String(255), nullable=True)

# ---------------------------------------------------------
# TREK REVIEW MODEL (New - For Analytics Dashboard)
# ---------------------------------------------------------
class TrekReview(db.Model):
    __tablename__ = 'trek_review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)