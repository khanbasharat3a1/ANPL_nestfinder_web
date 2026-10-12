import logging
from flask import Blueprint, jsonify, request, g
from ..constants import APP_NAME, APP_VERSION
from ..auth.decorators import login_required, not_banned
from ..extensions import limiter
from ..services.cloudinary_service import generate_upload_signature
from ..services.notifications_service import (
    get_unread_notification_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
)
from ..services.favorites_service import toggle_favorite
from ..services.listings_service import get_listing_by_id
from ..services.policy import can_access_review_queue, can_favorite_listing

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint for monitoring, load balancers, and container orchestrators."""
    return jsonify({
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
    }), 200


@api_bp.route("/uploads/sign", methods=["POST"])
@login_required
@not_banned
@limiter.limit("20 per minute")
def sign_upload():
    """Generates an authenticated upload signature for the signed preset."""
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        sign_data = generate_upload_signature(user["uid"])
        return jsonify(sign_data), 200
    except Exception as e:
        logger.error("Error generating upload signature for %s: %s", user.get("uid"), e)
        return jsonify({"error": "Failed to generate upload signature"}), 500


@api_bp.route("/counts/badges", methods=["GET"])
@login_required
def badge_counts():
    """Returns badge counts (review queue count for approvers, notifications for users)."""
    user = getattr(g, "user", None)
    uid = user["uid"]

    unread_notifs = get_unread_notification_count(uid)

    pending_reviews = 0
    if can_access_review_queue(user):
        try:
            from ..extensions import get_firestore_client
            db = get_firestore_client()
            snap = db.collection("listings").where("status", "==", "pending").count().get()
            pending_reviews = snap[0][0].value
        except Exception:
            pending_reviews = 0

    return jsonify({
        "pendingReviewCount": pending_reviews,
        "unreadNotificationsCount": unread_notifs,
    }), 200


@api_bp.route("/listings/<listing_id>/favorite", methods=["POST"])
@login_required
@not_banned
def api_toggle_favorite(listing_id):
    """AJAX endpoint for toggling favorite bookmark on a listing."""
    user = getattr(g, "user", None)
    listing = get_listing_by_id(listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    if not can_favorite_listing(user, listing):
        return jsonify({"error": "Cannot favorite this listing"}), 403

    data = request.get_json(silent=True) or {}
    is_favorite = bool(data.get("isFavorite", True))

    success = toggle_favorite(user["uid"], listing_id, is_favorite)
    if success:
        return jsonify({"status": "success", "isFavorite": is_favorite}), 200
    return jsonify({"error": "Failed to update favorite"}), 500


@api_bp.route("/notifications/<notif_id>/read", methods=["POST"])
@login_required
def api_mark_notification_read(notif_id):
    """Marks a single notification as read."""
    user = getattr(g, "user", None)
    success = mark_notification_as_read(user["uid"], notif_id)
    return jsonify({"status": "success" if success else "error"}), 200 if success else 500


@api_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def api_mark_all_notifications_read():
    """Marks all user notifications as read."""
    user = getattr(g, "user", None)
    success = mark_all_notifications_as_read(user["uid"])
    return jsonify({"status": "success" if success else "error"}), 200 if success else 500
