from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User, Booking
from datetime import datetime
from werkzeug.security import generate_password_hash

user_ops_bp = Blueprint('user_ops', __name__)

def is_trekker(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'trekker'

# --- 1. Book a Trek ---
@user_ops_bp.route('/book/<int:trek_id>', methods=['POST'])
@jwt_required()
def book_trek(trek_id):
    current_user_id = get_jwt_identity()
    
    if not is_trekker(current_user_id):
        return jsonify({"msg": "Only registered Trekkers can book routes."}), 403
        
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"msg": "Trek not found."}), 404
        
    # Validation 1: Is it open?
    if trek.status != 'Open':
        return jsonify({"msg": "This route is currently closed for booking."}), 400
        
    # Validation 2: Are there slots?
    if trek.available_slots <= 0:
        return jsonify({"msg": "This trek is completely sold out."}), 400
        
    # Validation 3: Duplicate Booking Check (Milestone 5 Requirement)
    existing_booking = Booking.query.filter_by(user_id=current_user_id, trek_id=trek_id).first()
    if existing_booking and existing_booking.status != 'Cancelled':
        return jsonify({"msg": "You have already booked this trek!"}), 409
        
    try:
        # Create the booking
        new_booking = Booking(
            user_id=current_user_id,
            trek_id=trek_id,
            status='Booked'
        )
        
        # Decrement the available slots securely
        trek.available_slots -= 1
        
        db.session.add(new_booking)
        db.session.commit()
        
        return jsonify({"msg": "Trek booked successfully! Adventure awaits."}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Booking failed due to a server error."}), 500

# --- 2. Get My Booking History ---
@user_ops_bp.route('/my-bookings', methods=['GET'])
@jwt_required()
def get_my_bookings():
    current_user_id = get_jwt_identity()
    
    if not is_trekker(current_user_id):
        return jsonify({"msg": "Unauthorized."}), 403
        
    # Join Booking and Trek tables to get full route details
    my_bookings = db.session.query(Booking, Trek).join(Trek).filter(Booking.user_id == current_user_id).all()
    
    history = []
    for booking, trek in my_bookings:
        history.append({
            "booking_id": booking.id,
            "trek_name": trek.name,
            "location": trek.location,
            "start_date": trek.start_date.strftime('%Y-%m-%d'),
            "duration": trek.duration,
            "status": booking.status,
            "booked_on": booking.booking_date.strftime('%Y-%m-%d') if hasattr(booking, 'booking_date') and booking.booking_date else 'N/A'
        })
        
    return jsonify(history), 200

# --- 3. Update User Profile ---
@user_ops_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != 'trekker':
        return jsonify({"msg": "Unauthorized."}), 403
        
    data = request.get_json()
    
    try:
        # Update email if provided
        if 'email' in data and data['email']:
            # Check if new email is already taken by someone else
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({"msg": "Email already in use."}), 409
            user.email = data['email']
            
        # Update password if provided
        if 'password' in data and data['password']:
            user.password_hash = generate_password_hash(data['password'])
            
        db.session.commit()
        return jsonify({"msg": "Profile updated successfully!"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Failed to update profile."}), 500