from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User
from datetime import datetime

trek_bp = Blueprint('trek', __name__)

# --- Helper Security Guard ---
def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'

# --- 1. Create a New Trek (Admin Only) ---
@trek_bp.route('/', methods=['POST'])
@jwt_required()
def create_trek():
    current_user_id = get_jwt_identity()
    
    # Security Check: Reject if not Admin
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403
        
    data = request.get_json()
    
    # Validation: Ensure all required fields are present
    required_fields = ['name', 'location', 'difficulty', 'duration', 'available_slots', 'start_date', 'end_date']
    for field in required_fields:
        if field not in data:
            return jsonify({"msg": f"Missing required field: {field}"}), 400
            
    try:
        # Parse the string dates into Python datetime objects
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        
        new_trek = Trek(
            name=data['name'],
            location=data['location'],
            difficulty=data['difficulty'],
            duration=int(data['duration']),
            available_slots=int(data['available_slots']),
            start_date=start_date,
            end_date=end_date,
            # Include our custom data-driven fields
            base_price=float(data.get('base_price', 0.0)),
            max_altitude=data.get('max_altitude'),
            staff_id=data.get('staff_id'),
            status='Open' # Automatically open it for booking
        )
        
        db.session.add(new_trek)
        db.session.commit()
        
        return jsonify({"msg": "Trek route created successfully!", "trek_id": new_trek.id}), 201
        
    except Exception as e:
        return jsonify({"msg": f"Data formatting error: {str(e)}"}), 500

# --- 2. Get All Treks ---
@trek_bp.route('/', methods=['GET'])
def get_all_treks():
    """Fetches all treks. Open to public so users can browse available routes."""
    treks = Trek.query.all()
    trek_list = []
    
    for t in treks:
        trek_list.append({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "difficulty": t.difficulty,
            "duration": t.duration,
            "available_slots": t.available_slots,
            "status": t.status,
            "start_date": t.start_date.strftime('%Y-%m-%d'),
            "end_date": t.end_date.strftime('%Y-%m-%d'),
            "base_price": t.base_price
        })
        
    return jsonify(trek_list), 200


# --- 3. Delete a Trek (Admin Only) ---
@trek_bp.route('/<int:trek_id>', methods=['DELETE'])
@jwt_required()
def delete_trek(trek_id):
    current_user_id = get_jwt_identity()
    
    # Security Check
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403
        
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"msg": "Trek not found"}), 404
        
    try:
        db.session.delete(trek)
        db.session.commit()
        return jsonify({"msg": "Trek deleted successfully"}), 200
    except Exception as e:
        return jsonify({"msg": "Failed to delete trek. It may have associated bookings."}), 500
    

# --- 4. Update a Trek (Admin Only) ---
@trek_bp.route('/<int:trek_id>', methods=['PUT'])
@jwt_required()
def update_trek(trek_id):
    current_user_id = get_jwt_identity()
    
    # Security Check
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403
        
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"msg": "Trek not found"}), 404
        
    data = request.get_json()
    
    try:
        # Update fields if they exist in the request
        trek.name = data.get('name', trek.name)
        trek.location = data.get('location', trek.location)
        trek.difficulty = data.get('difficulty', trek.difficulty)
        trek.duration = int(data.get('duration', trek.duration))
        trek.available_slots = int(data.get('available_slots', trek.available_slots))
        trek.base_price = float(data.get('base_price', trek.base_price))
        trek.max_altitude = data.get('max_altitude', trek.max_altitude)
        trek.staff_id = data.get('staff_id', trek.staff_id)
        
        # Only update dates if provided
        if data.get('start_date'):
            trek.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        if data.get('end_date'):
            trek.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
            
        db.session.commit()
        return jsonify({"msg": "Trek updated successfully!"}), 200
        
    except Exception as e:
        return jsonify({"msg": f"Failed to update trek: {str(e)}"}), 500