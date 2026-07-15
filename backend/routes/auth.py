from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User

auth_bp = Blueprint('auth', __name__)

# --- User Registration (Trekkers Only) ---
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"msg": "Missing required authentication fields."}), 400
        
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({"msg": "This email is already registered."}), 409
        
    try:
        hashed_password = generate_password_hash(data['password'])
        
        # NEW: Capture advanced profile data during registration
        new_user = User(
            email=data['email'],
            password_hash=hashed_password,
            role='trekker',
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            emergency_contact=data.get('emergency_contact', ''),
            experience_level=data.get('experience_level', 'Beginner'),
            medical_conditions=data.get('medical_conditions', 'None')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({"msg": "Account created successfully! Welcome to OnTreq."}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Registration failed: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handles login for Admin, Staff, and Trekkers."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Invalid email or password"}), 401
        
    if not user.is_active:
        return jsonify({"msg": "Account is deactivated"}), 403
        
    # Generate the secure token.
    # FIX: identity is just the user id string (required by flask-jwt-extended),
    # but the frontend was previously trying to read `payload.sub.email` off the
    # decoded token, which never existed - additional_claims puts email/role at
    # the top level of the JWT payload so the frontend can read them directly.
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"email": user.email, "role": user.role, "first_name": user.first_name or ""}
    )
    
    return jsonify({
        "token": access_token,
        "role": user.role,
        "email": user.email,
        "first_name": user.first_name or "",
        "id": user.id
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Lets any logged-in page fetch fresh profile info instead of guessing from the JWT."""
    from flask_jwt_extended import get_jwt_identity
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active
    }), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_own_profile():
    """NEW: generic 'update my own account' endpoint for ANY logged-in role
    (Admin/Staff/Trekker). Previously only trekkers could update their profile
    (via /api/user-ops/profile) - Admin's "Settings" nav link went nowhere
    because there was no page and no backend route for it."""
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() or {}

    try:
        if data.get('email'):
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({"msg": "Email already in use."}), 409
            user.email = data['email']

        if data.get('first_name'):
            user.first_name = data['first_name']
        if data.get('last_name'):
            user.last_name = data['last_name']
        if data.get('phone'):
            user.phone = data['phone']

        if data.get('password'):
            if len(data['password']) < 6:
                return jsonify({"msg": "Password must be at least 6 characters."}), 400
            user.password_hash = generate_password_hash(data['password'])

        db.session.commit()
        return jsonify({"msg": "Account settings updated successfully."}), 200

    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Failed to update settings due to a server error."}), 500