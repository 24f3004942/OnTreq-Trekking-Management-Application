from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Trek, User, Booking, cache
from datetime import datetime
from werkzeug.security import generate_password_hash
import os

user_ops_bp = Blueprint('user_ops', __name__)


def is_trekker(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'trekker'


def _invalidate_trek_caches():
    # Fail-soft: a transient Redis hiccup must never turn an already-committed
    # write into a reported "failure" for the user.
    try:
        for key in ('public_treks', 'admin_stats', 'admin_analytics', 'public_stats'):
            cache.delete(key)
    except Exception:
        pass


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

    if trek.status != 'Open':
        return jsonify({"msg": "This route is currently closed for booking."}), 400

    if trek.available_slots <= 0:
        return jsonify({"msg": "This trek is completely sold out."}), 400

    # Duplicate Booking Check - only blocks if there's a currently-active
    # (Booked) record; a user who previously cancelled is allowed to re-book.
    existing_booking = Booking.query.filter_by(user_id=current_user_id, trek_id=trek_id).first()
    if existing_booking and existing_booking.status == 'Booked':
        return jsonify({"msg": "You have already booked this trek!"}), 409

    try:
        new_booking = Booking(
            user_id=current_user_id,
            trek_id=trek_id,
            status='Booked',
            # The frontend already runs a simulated payment step (payment
            # modal + fake processing delay) before this endpoint is called,
            # so we mark payment as settled here instead of leaving it stuck
            # on the default 'Pending' forever.
            payment_status='Paid'
        )

        trek.available_slots -= 1

        db.session.add(new_booking)
        db.session.commit()
        _invalidate_trek_caches()

        return jsonify({"msg": "Trek booked successfully! Adventure awaits."}), 201

    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Booking failed due to a server error."}), 500


# --- 2. Cancel a Booking ---
@user_ops_bp.route('/my-bookings/<int:booking_id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_booking(booking_id):
    """NEW: previously there was no way for a booking to ever become
    'Cancelled' anywhere in the app, even though the schema/wireframe both
    call for that status. This closes that gap."""
    current_user_id = get_jwt_identity()

    if not is_trekker(current_user_id):
        return jsonify({"msg": "Unauthorized."}), 403

    booking = Booking.query.get(booking_id)
    if not booking or str(booking.user_id) != str(current_user_id):
        return jsonify({"msg": "Booking not found."}), 404

    if booking.status != 'Booked':
        return jsonify({"msg": f"This booking is already {booking.status.lower()} and cannot be cancelled."}), 400

    trek = Trek.query.get(booking.trek_id)
    if trek and trek.status == 'Completed':
        return jsonify({"msg": "This trek has already been completed and cannot be cancelled."}), 400

    try:
        booking.status = 'Cancelled'
        if trek:
            trek.available_slots += 1
        db.session.commit()
        _invalidate_trek_caches()
        return jsonify({"msg": "Booking cancelled. Your slot has been released."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Failed to cancel booking due to a server error."}), 500


# --- 3. Get My Booking History ---
@user_ops_bp.route('/my-bookings', methods=['GET'])
@jwt_required()
def get_my_bookings():
    current_user_id = get_jwt_identity()

    if not is_trekker(current_user_id):
        return jsonify({"msg": "Unauthorized."}), 403

    my_bookings = db.session.query(Booking, Trek).join(Trek) \
        .filter(Booking.user_id == current_user_id) \
        .order_by(Booking.id.desc()).all()

    history = []
    for booking, trek in my_bookings:
        history.append({
            "booking_id": booking.id,
            "trek_id": trek.id,
            "trek_name": trek.name,
            "location": trek.location,
            "start_date": trek.start_date.strftime('%Y-%m-%d') if trek.start_date else None,
            "duration": trek.duration,
            "status": booking.status,
            "payment_status": booking.payment_status,
            "booked_on": booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else 'N/A',
            # Wireframe screen 12 ("Trekking History") shows a "Completed On"
            # column - expose the last status-change timestamp for
            # Completed/Cancelled bookings.
            "completed_on": booking.updated_at.strftime('%Y-%m-%d') if booking.status != 'Booked' and booking.updated_at else None
        })

    return jsonify(history), 200


# --- 4. Update User Profile ---
@user_ops_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user or user.role != 'trekker':
        return jsonify({"msg": "Unauthorized."}), 403

    data = request.get_json()

    try:
        if 'email' in data and data['email']:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({"msg": "Email already in use."}), 409
            user.email = data['email']

        if 'first_name' in data and data['first_name']:
            user.first_name = data['first_name']
        if 'last_name' in data and data['last_name']:
            user.last_name = data['last_name']
        if 'phone' in data and data['phone']:
            user.phone = data['phone']

        if 'password' in data and data['password']:
            user.password_hash = generate_password_hash(data['password'])

        db.session.commit()
        return jsonify({"msg": "Profile updated successfully!"}), 200

    except Exception:
        db.session.rollback()
        return jsonify({"msg": "Failed to update profile."}), 500


# --- 5. Trigger Async CSV Export (Milestone 7) ---
@user_ops_bp.route('/export', methods=['POST'])
@jwt_required()
def trigger_export():
    from jobs.tasks import export_booking_history

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    task = export_booking_history.delay(current_user_id, user.email)

    return jsonify({"msg": "Export job initialized.", "task_id": task.id}), 202


# --- 6. Check Async Job Status ---
@user_ops_bp.route('/export/status/<task_id>', methods=['GET'])
@jwt_required()
def check_export_status(task_id):
    # FIX (found during testing): `AsyncResult(task_id)` from `celery.result`
    # binds to Celery's *default* app, which has no result backend configured
    # (DisabledBackend) - every call raised AttributeError even though the
    # worker had already finished the task correctly. Using the app instance
    # that actually has `result_backend='redis://...'` set (app.celery_app)
    # fixes status polling.
    from app import celery_app
    task = celery_app.AsyncResult(task_id)

    if task.state in ('PENDING', 'STARTED'):
        return jsonify({"state": task.state, "msg": "Processing data in background..."}), 200
    elif task.state == 'SUCCESS':
        return jsonify({"state": task.state, "msg": "Export complete!", "filename": task.result['file']}), 200
    else:
        return jsonify({"state": task.state, "msg": "Export failed."}), 500


# --- 7. Download the CSV File ---
@user_ops_bp.route('/export/download/<filename>', methods=['GET'])
def download_export(filename):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'exports', filename))
    try:
        return send_file(filepath, as_attachment=True)
    except Exception:
        return jsonify({"msg": "File not found on server."}), 404
