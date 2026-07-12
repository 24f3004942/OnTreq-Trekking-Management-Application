from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User, Booking

staff_ops_bp = Blueprint('staff_ops', __name__)

# --- Helper Security Guard ---
def is_staff(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'staff'

# --- 1. Get Assigned Treks ---
@staff_ops_bp.route('/my-treks', methods=['GET'])
@jwt_required()
def get_my_treks():
    current_user_id = get_jwt_identity()
    
    if not is_staff(current_user_id):
        return jsonify({"msg": "Unauthorized. Staff access required."}), 403
        
    # Find only the treks assigned to this specific staff member
    my_treks = Trek.query.filter_by(staff_id=current_user_id).all()
    
    trek_list = []
    for t in my_treks:
        # Count how many people have booked this trek (for the dashboard)
        participant_count = Booking.query.filter_by(trek_id=t.id, status='Booked').count()
        
        trek_list.append({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "status": t.status,
            "available_slots": t.available_slots,
            "start_date": t.start_date.strftime('%Y-%m-%d'),
            "participants": participant_count
        })
        
    return jsonify(trek_list), 200

# --- 2. Update Trek Status & Slots ---
@staff_ops_bp.route('/my-treks/<int:trek_id>', methods=['PUT'])
@jwt_required()
def update_my_trek(trek_id):
    current_user_id = get_jwt_identity()
    
    if not is_staff(current_user_id):
        return jsonify({"msg": "Unauthorized."}), 403
        
    trek = Trek.query.get(trek_id)
    
    # SECURITY: Ensure this trek actually belongs to this staff member
    if not trek or str(trek.staff_id) != str(current_user_id):
        return jsonify({"msg": "Trek not found or not assigned to you."}), 404
        
    data = request.get_json()
    
    try:
        # Staff are only allowed to update these two specific fields!
        if 'status' in data:
            # Validate status
            allowed_statuses = ['Open', 'Closed', 'Ongoing', 'Completed']
            if data['status'] in allowed_statuses:
                trek.status = data['status']
                
        if 'available_slots' in data:
            trek.available_slots = int(data['available_slots'])
            
        db.session.commit()
        return jsonify({"msg": "Trek updated successfully!"}), 200
        
    except Exception as e:
        return jsonify({"msg": f"Failed to update trek: {str(e)}"}), 500
    
# --- 3. View Trek Participants ---
@staff_ops_bp.route('/my-treks/<int:trek_id>/participants', methods=['GET'])
@jwt_required()
def get_trek_participants(trek_id):
    current_user_id = get_jwt_identity()
    
    if not is_staff(current_user_id):
        return jsonify({"msg": "Unauthorized."}), 403
        
    trek = Trek.query.get(trek_id)
    if not trek or str(trek.staff_id) != str(current_user_id):
        return jsonify({"msg": "Trek not found or not assigned to you."}), 404
        
    # Fetch all bookings for this trek
    bookings = Booking.query.filter_by(trek_id=trek_id).all()
    participants = []
    
    for b in bookings:
        user = User.query.get(b.user_id)
        if user:
            participants.append({
                "booking_id": b.id,
                "user_id": user.id,
                "email": user.email,
                "booking_status": b.status,
                # Safe date formatting if booking_date exists
                "date": b.booking_date.strftime('%Y-%m-%d') if hasattr(b, 'booking_date') and b.booking_date else 'N/A'
            })
            
    return jsonify(participants), 200