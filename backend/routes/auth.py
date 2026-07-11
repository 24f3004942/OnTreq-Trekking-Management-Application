from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Only Users (Trekkers) can self-register."""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409
        
    # Create the new Trekker
    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email,
        password_hash=hashed_password,
        role='trekker' # Hardcoded to trekker so no one can self-register as admin/staff
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "User registered successfully"}), 201

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
        
    # Generate the secure token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "token": access_token,
        "role": user.role,
        "email": user.email,
        "id": user.id
    }), 200