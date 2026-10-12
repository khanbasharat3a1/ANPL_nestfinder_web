from flask import Blueprint, jsonify, g
from ..constants import APP_NAME, APP_VERSION
from ..auth.decorators import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint for monitoring, load balancers, and container orchestrators."""
    return jsonify({
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
    }), 200


@api_bp.route("/counts/badges", methods=["GET"])
@login_required
def badge_counts():
    """Returns badge counts (pending reviews for approvers, notifications for users)."""
    user = getattr(g, "user", None)
    return jsonify({
        "pendingReviewCount": 0,
        "unreadNotificationsCount": 0,
    }), 200
