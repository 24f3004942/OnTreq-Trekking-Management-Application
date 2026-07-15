from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from models import db, User, StaffProfile, cache

staff_bp = Blueprint('staff', __name__)


def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'


def _invalidate_staff_cache():
    try:
        cache.delete('staff_list')
        cache.delete('admin_stats')
    except Exception:
        pass


# --- 1. Recruit New Staff (Admin Only) ---
@staff_bp.route('/', methods=['POST'])
@jwt_required()
def create_staff():
    current_user_id = get_jwt_identity()

    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    data = request.get_json()

    required_fields = ['email', 'password', 'name', 'contact']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"msg": f"Missing required field: {field}"}), 400

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
        db.session.flush()  # Flush gets the new_user.id before full commit

        # Step 2: Create the linked staff profile.
        # FIX (bug #2): this used to pass `contact_details=...` into a model
        # that only had a `phone` column -> TypeError on every single staff
        # creation attempt. The model field is now named `contact_details` to
        # match, so this line is correct again.
        new_profile = StaffProfile(
            user_id=new_user.id,
            name=data['name'],
            contact_details=data['contact'],
            years_experience=data.get('years_experience', 0),
            certifications=data.get('certifications', '')
        )
        db.session.add(new_profile)
        db.session.commit()
        _invalidate_staff_cache()

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

    term = request.args.get('q', '').strip()

    # Cache only the unfiltered "full roster" call - search results stay live.
    if not term:
        try:
            cached = cache.get('staff_list')
        except Exception:
            cached = None
        if cached is not None:
            return jsonify(cached), 200

    query = db.session.query(User, StaffProfile).join(StaffProfile).filter(User.role == 'staff')
    if term:
        like = f"%{term}%"
        query = query.filter(db.or_(User.email.ilike(like), StaffProfile.name.ilike(like)))

    staff_members = query.all()

    staff_list = []
    for user, profile in staff_members:
        staff_list.append({
            "id": user.id,
            "email": user.email,
            "name": profile.name,
            "contact": profile.contact_details,
            "years_experience": profile.years_experience,
            "certifications": profile.certifications,
            "is_active": user.is_active,
            "joined": user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'
        })

    if not term:
        try:
            cache.set('staff_list', staff_list, timeout=60)
        except Exception:
            pass

    return jsonify(staff_list), 200


# --- 3. Blacklist / Reactivate Staff (soft, reversible - keeps their history intact) ---
@staff_bp.route('/<int:user_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_staff_status(user_id):
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    user = User.query.get(user_id)
    if not user or user.role != 'staff':
        return jsonify({"msg": "Staff member not found."}), 404

    user.is_active = not user.is_active
    db.session.commit()
    _invalidate_staff_cache()

    status_text = "reactivated" if user.is_active else "blacklisted"
    return jsonify({"msg": f"Staff account successfully {status_text}.", "is_active": user.is_active}), 200


# --- 4. Revoke Staff Access (hard delete) ---
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
        _invalidate_staff_cache()
        return jsonify({"msg": "Staff access revoked and profile deleted."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Cannot delete staff. They may have active trek assignments. Try blacklisting instead."}), 500
