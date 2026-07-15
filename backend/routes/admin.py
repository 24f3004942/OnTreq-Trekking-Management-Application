from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Trek, Booking, StaffProfile, cache
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == 'admin'


def _invalidate_admin_caches():
    """Central place to bust every cache key admin.py owns, so every mutating
    route stays consistent instead of each one remembering its own key list.
    Fail-soft so a Redis hiccup never fails an already-committed write."""
    try:
        for key in ('admin_stats', 'admin_analytics'):
            cache.delete(key)
    except Exception:
        pass


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@cache.cached(timeout=30, key_prefix='admin_stats')
def get_dashboard_stats():
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
    """Fetch all standard users (trekkers) for the admin dashboard.
    Supports ?q=<term> server-side search on email/name (Milestone 3:
    'Search users, staff, or treks'), in addition to the client-side filter
    that already existed on the frontend."""
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized"}), 403

    query = User.query.filter_by(role='trekker')
    term = request.args.get('q', '').strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            db.or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like)
            )
        )

    users = query.all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "is_active": u.is_active,
            "joined": u.created_at.strftime('%Y-%m-%d') if u.created_at else 'N/A'
        })

    return jsonify(user_list), 200


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_user_status(user_id):
    """Allows admin to blacklist/deactivate any non-admin account
    (trekker OR staff - kept generic on purpose since both roles need this)."""
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized. Admin access required."}), 403

    user = User.query.get(user_id)
    if not user or user.role == 'admin':
        return jsonify({"msg": "Invalid user."}), 400

    user.is_active = not user.is_active
    db.session.commit()
    _invalidate_admin_caches()

    status_text = "activated" if user.is_active else "blacklisted"
    return jsonify({"msg": f"User account successfully {status_text}.", "is_active": user.is_active}), 200


@admin_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_all_bookings():
    """Fetch every booking in the system for the Admin.
    Supports ?q=<term> to search by user email or trek name."""
    current_user_id = get_jwt_identity()
    if not is_admin(current_user_id):
        return jsonify({"msg": "Unauthorized"}), 403

    records = db.session.query(Booking, User, Trek) \
        .join(User, Booking.user_id == User.id) \
        .join(Trek, Booking.trek_id == Trek.id).order_by(Booking.id.desc()).all()

    term = request.args.get('q', '').strip().lower()

    booking_list = []
    for booking, user, trek in records:
        if term and term not in user.email.lower() and term not in trek.name.lower() and term != str(booking.id):
            continue
        booking_list.append({
            "id": booking.id,
            "user_email": user.email,
            "trek_name": trek.name,
            "status": booking.status,
            "payment_status": booking.payment_status,
            "date": booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else 'N/A'
        })

    return jsonify(booking_list), 200


@admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@cache.cached(timeout=60, key_prefix='admin_analytics')
def get_chart_analytics():
    """Provides data for Chart.js dashboard"""
    easy = Trek.query.filter_by(difficulty='Easy').count()
    mod = Trek.query.filter_by(difficulty='Moderate').count()
    hard = Trek.query.filter_by(difficulty='Hard').count()
    extreme = Trek.query.filter_by(difficulty='Extreme').count()

    booked = Booking.query.filter_by(status='Booked').count()
    cancelled = Booking.query.filter_by(status='Cancelled').count()
    completed = Booking.query.filter_by(status='Completed').count()

    # Popular treks (by total bookings) - reused by the public landing page too
    popular = db.session.query(Trek.name, func.count(Booking.id).label('total')) \
        .join(Booking).group_by(Trek.id).order_by(db.desc('total')).limit(5).all()

    return jsonify({
        "difficulty_chart": [easy, mod, hard, extreme],
        "booking_status_chart": [booked, cancelled, completed],
        "popular_treks": [{"name": name, "bookings": total} for name, total in popular]
    }), 200
