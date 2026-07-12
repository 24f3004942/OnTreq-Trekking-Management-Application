from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from models import db, User, StaffProfile

staff_bp = Blueprint('staff', __name__)

# --- Helper Security Guard ---
def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'

# --- 1. Recruit New Staff (Admin Only) ---
@staff_bp.route('/', methods=['POST'])
@jwt_required()
def create_staff():
    current_user_id = get_jwt_identity()
    
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403
        
    data = request.get_json()
    
    # Check if email already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"msg": "Email is already registered in the system."}), 409
        
    try:
        # Step 1: Create the secure login account
        hashed_password = generate_password_hash(data['password'])
        new_user = User(
            email=data['email'],
            password_hash=hashed_password,
            role='staff'
        )
        db.session.add(new_user)
        db.session.flush() # Flush gets the new_user.id before full commit
        
        # Step 2: Create the linked staff profile
        new_profile = StaffProfile(
            user_id=new_user.id,
            name=data['name'],
            contact_details=data['contact']
        )
        db.session.add(new_profile)
        db.session.commit()
        
        return jsonify({"msg": "Staff member successfully recruited and account created!"}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to create staff: {str(e)}"}), 500

# --- 2. Get All Staff ---
@staff_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_staff():
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized"}), 403
        
    # Join User and StaffProfile to get full details
    staff_members = db.session.query(User, StaffProfile).join(StaffProfile).filter(User.role == 'staff').all()
    
    staff_list = []
    for user, profile in staff_members:
        staff_list.append({
            "id": user.id,
            "email": user.email,
            "name": profile.name,
            "contact": profile.contact_details,
            "is_active": user.is_active,
            "joined": user.created_at.strftime('%Y-%m-%d')
        })
        
    return jsonify(staff_list), 200

# --- 3. Revoke Staff Access ---
@staff_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_staff(user_id):
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized"}), 403
        
    user = User.query.get(user_id)
    if not user or user.role != 'staff':
        return jsonify({"msg": "Staff member not found"}), 404
        
    try:
        # Because of cascade="all, delete-orphan" in our models, 
        # deleting the user automatically deletes the StaffProfile!
        db.session.delete(user)
        db.session.commit()
        return jsonify({"msg": "Staff access revoked and profile deleted."}), 200
    except Exception as e:
        return jsonify({"msg": "Cannot delete staff. They may have active trek assignments."}), 500