from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Trek, Booking

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    # Only admins should access this (we will add strict role checking later)
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_treks = Trek.query.count()
    total_bookings = Booking.query.count()
    
    return jsonify({
        "users": total_users,
        "staff": total_staff,
        "treks": total_treks,
        "bookings": total_bookings
    }), 200


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """Fetch all standard users (trekkers) for the admin dashboard."""
    users = User.query.filter_by(role='trekker').all()
    user_list = []
    
    for u in users:
        user_list.append({
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "joined": u.created_at.strftime('%Y-%m-%d')
        })
        
    return jsonify(user_list), 200

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_user_status(user_id):
    """Allows admin to blacklist/deactivate a user."""
    user = User.query.get(user_id)
    if not user or user.role == 'admin':
        return jsonify({"msg": "Invalid user."}), 400
        
    # Toggle the active status
    user.is_active = not user.is_active
    db.session.commit()
    
    status_text = "activated" if user.is_active else "blacklisted"
    return jsonify({"msg": f"User account successfully {status_text}."}), 200

from backend.models import Booking, Trek

@admin_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_all_bookings():
    """Fetch every booking in the system for the Admin."""
    # Join Booking, User, and Trek tables
    records = db.session.query(Booking, User, Trek)\
        .join(User, Booking.user_id == User.id)\
        .join(Trek, Booking.trek_id == Trek.id).all()
        
    booking_list = []
    for booking, user, trek in records:
        booking_list.append({
            "id": booking.id,
            "user_email": user.email,
            "trek_name": trek.name,
            "status": booking.status,
            "date": booking.booking_date.strftime('%Y-%m-%d') if hasattr(booking, 'booking_date') and booking.booking_date else 'N/A'
        })
        
    return jsonify(booking_list), 200