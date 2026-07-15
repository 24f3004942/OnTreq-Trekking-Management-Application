from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User, Booking, cache

staff_ops_bp = Blueprint('staff_ops', __name__)


def is_staff(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'staff'


def _invalidate_trek_caches():
    # Fail-soft: a transient Redis hiccup must never turn an already-committed
    # write into a reported "failure" for the user.
    try:
        for key in ('public_treks', 'admin_stats', 'admin_analytics', 'public_stats'):
            cache.delete(key)
    except Exception:
        pass


# --- 1. Get Assigned Treks ---
@staff_ops_bp.route('/my-treks', methods=['GET'])
@jwt_required()
def get_my_treks():
    current_user_id = get_jwt_identity()

    if not is_staff(current_user_id):
        return jsonify({"msg": "Unauthorized. Staff access required."}), 403

    my_treks = Trek.query.filter_by(staff_id=current_user_id).all()

    trek_list = []
    for t in my_treks:
        participant_count = Booking.query.filter_by(trek_id=t.id, status='Booked').count()

        trek_list.append({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "status": t.status,
            "difficulty": t.difficulty,
            "available_slots": t.available_slots,
            "start_date": t.start_date.strftime('%Y-%m-%d') if t.start_date else None,
            "end_date": t.end_date.strftime('%Y-%m-%d') if t.end_date else None,
            # NOTE: kept as `participants` (not `participant_count`) because
            # staff_dashboard.html already reads `trek.participants` for the
            # per-row badge - renaming the key here would just move the bug
            # instead of fixing it. The dashboard-total computed property was
            # the actual mismatch, fixed on the frontend side instead.
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

    if not trek or str(trek.staff_id) != str(current_user_id):
        return jsonify({"msg": "Trek not found or not assigned to you."}), 404

    data = request.get_json()

    try:
        if 'status' in data:
            allowed_statuses = ['Open', 'Closed', 'Ongoing', 'Completed']
            if data['status'] in allowed_statuses:
                trek.status = data['status']
                # Cascade booking status when a trek finishes, so booking
                # history (Milestone 6) reflects reality instead of every
                # booking staying "Booked" forever.
                if data['status'] == 'Completed':
                    Booking.query.filter_by(trek_id=trek.id, status='Booked').update({"status": "Completed"})

        if 'available_slots' in data:
            new_slots = int(data['available_slots'])
            if new_slots < 0:
                return jsonify({"msg": "Available slots cannot be negative."}), 400
            trek.available_slots = new_slots

        db.session.commit()
        _invalidate_trek_caches()
        return jsonify({"msg": "Trek updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
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
                "payment_status": b.payment_status,
                "date": b.booking_date.strftime('%Y-%m-%d') if b.booking_date else 'N/A'
            })

    return jsonify(participants), 200
