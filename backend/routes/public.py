from flask import Blueprint, jsonify
from models import db, Trek, Booking, User, cache
from sqlalchemy import func

public_bp = Blueprint('public', __name__)


@public_bp.route('/stats', methods=['GET'])
@cache.cached(timeout=60, key_prefix='public_stats')
def public_stats():
    """NEW: Milestone 10 (optional but listed as a core wireframe screen) asks
    for a 'Public Landing Dashboard Page (pre-login) showing trekking
    statistics (read-only, no sensitive data)'. Previously index.html just
    hacked together one inline stat with a broken DOM selector
    (`.auth-card`, which didn't exist) - this gives it a real, cacheable,
    no-auth endpoint with only non-sensitive aggregate numbers."""
    open_treks = Trek.query.filter_by(status='Open').count()
    total_treks = Trek.query.count()
    completed_treks = Trek.query.filter_by(status='Completed').count()
    total_trekkers = User.query.filter_by(role='trekker').count()

    popular = db.session.query(Trek.name, func.count(Booking.id).label('total')) \
        .join(Booking).group_by(Trek.id).order_by(db.desc('total')).limit(3).all()

    return jsonify({
        "open_treks": open_treks,
        "total_treks": total_treks,
        "completed_treks": completed_treks,
        "total_trekkers": total_trekkers,
        "popular_treks": [name for name, _ in popular]
    }), 200
