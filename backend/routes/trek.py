from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User, Booking, cache
from datetime import datetime

trek_bp = Blueprint('trek', __name__)


def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'


def _invalidate_trek_caches():
    # Fail-soft: a transient Redis hiccup must never turn an already-committed
    # write into a reported "failure" for the user.
    try:
        for key in ('public_treks', 'admin_stats', 'admin_analytics', 'public_stats'):
            cache.delete(key)
    except Exception:
        pass


def _serialize_trek(t):
    return {
        "id": t.id,
        "name": t.name,
        "location": t.location,
        "difficulty": t.difficulty,
        "duration": t.duration,
        "available_slots": t.available_slots,
        "staff_id": t.staff_id,
        "status": t.status,
        "start_date": t.start_date.strftime('%Y-%m-%d') if t.start_date else None,
        "end_date": t.end_date.strftime('%Y-%m-%d') if t.end_date else None,
        "base_price": t.base_price,
        "max_altitude": t.max_altitude
    }


# --- 1. Create a New Trek (Admin Only) ---
@trek_bp.route('/', methods=['POST'])
@jwt_required()
def create_trek():
    current_user_id = get_jwt_identity()

    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    data = request.get_json()

    required_fields = ['name', 'location', 'difficulty', 'duration', 'available_slots', 'start_date', 'end_date']
    for field in required_fields:
        if not data.get(field) and data.get(field) != 0:
            return jsonify({"msg": f"Missing required field: {field}"}), 400

    try:
        # FIX: model columns are now `Date`, so parse down to .date() -
        # previously a full datetime object was stored into a String column,
        # which only "worked" until the app restarted and re-read the row.
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

        if start_date < datetime.utcnow().date():
            return jsonify({"msg": "Start date cannot be in the past."}), 400
        if end_date < start_date:
            return jsonify({"msg": "End date cannot be before the start date."}), 400
        if int(data['available_slots']) < 0:
            return jsonify({"msg": "Available slots cannot be negative."}), 400

        new_trek = Trek(
            name=data['name'],
            location=data['location'],
            difficulty=data['difficulty'],
            duration=int(data['duration']),
            available_slots=int(data['available_slots']),
            start_date=start_date,
            end_date=end_date,
            base_price=float(data.get('base_price', 0.0)),
            max_altitude=data.get('max_altitude') or None,
            staff_id=data.get('staff_id') or None,
            status='Open'
        )

        db.session.add(new_trek)
        db.session.commit()
        _invalidate_trek_caches()
        return jsonify({"msg": "Trek route created successfully!", "trek_id": new_trek.id}), 201

    except ValueError as e:
        return jsonify({"msg": f"Invalid date or numeric field: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Data formatting error: {str(e)}"}), 500


# --- 2. Get All Treks (with optional server-side search/filter) ---
@trek_bp.route('/', methods=['GET'])
def get_all_treks():
    """Fetches treks. Open to public so users can browse available routes.
    Supports ?q= (name/location), ?difficulty=, ?location=, ?max_duration=
    for server-side filtering (Milestone 5: 'search and filter treks based on
    difficulty, location, and duration'), on top of the client-side filter
    that already existed in the Vue frontend."""
    q = request.args.get('q', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    location = request.args.get('location', '').strip()
    max_duration = request.args.get('max_duration', '').strip()

    # Only the unfiltered "browse all" call is cache-worthy; filtered/search
    # queries are cheap enough and stay live so results are always fresh.
    if not any([q, difficulty, location, max_duration]):
        try:
            cached = cache.get('public_treks')
        except Exception:
            cached = None
        if cached is not None:
            return jsonify(cached), 200

    query = Trek.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like)))
    if difficulty:
        query = query.filter(Trek.difficulty == difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f"%{location}%"))
    if max_duration:
        try:
            query = query.filter(Trek.duration <= int(max_duration))
        except ValueError:
            pass

    treks = query.order_by(Trek.id.desc()).all()
    trek_list = [_serialize_trek(t) for t in treks]

    if not any([q, difficulty, location, max_duration]):
        try:
            cache.set('public_treks', trek_list, timeout=60)
        except Exception:
            pass

    return jsonify(trek_list), 200


# --- 3. Delete a Trek (Admin Only) ---
@trek_bp.route('/<int:trek_id>', methods=['DELETE'])
@jwt_required()
def delete_trek(trek_id):
    current_user_id = get_jwt_identity()

    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"msg": "Trek not found"}), 404

    try:
        db.session.delete(trek)
        db.session.commit()
        _invalidate_trek_caches()
        return jsonify({"msg": "Trek deleted successfully"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Failed to delete trek. It may have associated bookings."}), 500


# --- 4. Update a Trek (Admin Only) ---
@trek_bp.route('/<int:trek_id>', methods=['PUT'])
@jwt_required()
def update_trek(trek_id):
    current_user_id = get_jwt_identity()

    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"msg": "Trek not found"}), 404

    data = request.get_json()

    try:
        trek.name = data.get('name', trek.name)
        trek.location = data.get('location', trek.location)
        trek.difficulty = data.get('difficulty', trek.difficulty)
        trek.duration = int(data.get('duration', trek.duration))

        new_slots = int(data.get('available_slots', trek.available_slots))
        if new_slots < 0:
            return jsonify({"msg": "Available slots cannot be negative."}), 400
        trek.available_slots = new_slots

        trek.base_price = float(data.get('base_price', trek.base_price))
        trek.max_altitude = data.get('max_altitude', trek.max_altitude)
        trek.staff_id = data.get('staff_id', trek.staff_id)

        if data.get('status'):
            trek.status = data['status']

        if data.get('start_date'):
            new_start = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if new_start != trek.start_date and new_start < datetime.utcnow().date():
                return jsonify({"msg": "Start date cannot be in the past."}), 400
            trek.start_date = new_start
        if data.get('end_date'):
            trek.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

        if trek.end_date < trek.start_date:
            db.session.rollback()
            return jsonify({"msg": "End date cannot be before the start date."}), 400

        # Cascade: if admin marks a trek Completed directly, close out any
        # bookings still sitting in 'Booked' so booking history stays honest.
        if trek.status == 'Completed':
            Booking.query.filter_by(trek_id=trek.id, status='Booked').update({"status": "Completed"})

        db.session.commit()
        _invalidate_trek_caches()
        return jsonify({"msg": "Trek updated successfully!"}), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({"msg": f"Invalid date or numeric field: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update trek: {str(e)}"}), 500
