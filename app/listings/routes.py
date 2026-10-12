import logging
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    abort,
    current_app,
    g,
    flash,
)
from ..auth.decorators import login_required, not_banned
from ..constants import STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED
from ..extensions import limiter
from ..services.config_service import get_app_config
from ..services.cloudinary_service import transform_photo_url
from ..services.policy import (
    can_view_listing,
    can_create_listing,
    can_edit_listing,
    can_archive_listing,
    can_view_reviewer_details,
    can_report_listing,
)
from ..services.listings_service import (
    fetch_approved_listings,
    get_listing_by_id,
    create_listing,
    update_listing,
    archive_listing,
    fetch_my_listings,
)
from ..services.favorites_service import (
    get_user_favorite_ids,
    fetch_favorite_listings,
)
from ..services.reports_service import has_user_reported, submit_report
from .validators import validate_listing_payload

logger = logging.getLogger(__name__)

listings_bp = Blueprint("listings", __name__)


@listings_bp.route("/")
def index():
    """Root entry point redirects to Explore feed."""
    return redirect(url_for("listings.explore"))


@listings_bp.route("/explore")
def explore():
    """
    Explore feed displaying approved accommodation listings with filters and cursor pagination.
    """
    filters = {
        "type": request.args.get("type"),
        "furnishing": request.args.get("furnishing"),
        "genderPreference": request.args.get("gender"),
        "locality": request.args.get("locality"),
        "minRent": request.args.get("minRent"),
        "maxRent": request.args.get("maxRent"),
        "sortBy": request.args.get("sortBy", "newest"),
        "searchQuery": request.args.get("q", ""),
    }

    # Filter out empty string values
    clean_filters = {k: v for k, v in filters.items() if v not in (None, "")}

    cursor_token = request.args.get("cursor")
    secret_key = current_app.config.get("SECRET_KEY", "secret")

    result = fetch_approved_listings(
        filters=clean_filters,
        cursor_token=cursor_token,
        secret_key=secret_key,
    )

    # Transform card photos for fast loading
    for item in result["listings"]:
        if item.get("coverPhoto"):
            item["cardPhoto"] = transform_photo_url(item["coverPhoto"], mode="card")

    app_config = get_app_config()
    user = getattr(g, "user", None)
    fav_ids = get_user_favorite_ids(user["uid"]) if user else set()

    return render_template(
        "listings/explore.html",
        listings=result["listings"],
        has_more=result["hasMore"],
        next_cursor=result["nextCursor"],
        current_filters=filters,
        app_config=app_config,
        favorite_ids=fav_ids,
    )


@listings_bp.route("/listings/<listing_id>")
def detail(listing_id):
    """
    Detailed accommodation view:
    Photo carousel, verified badge, property specifications, amenities, and sticky contact bar.
    """
    listing = get_listing_by_id(listing_id)
    if not listing:
        abort(404)

    user = getattr(g, "user", None)
    if not can_view_listing(user, listing):
        abort(403)

    # Pre-transform photos for high-res detail viewing
    raw_photos = listing.get("photos", [])
    detail_photos = [transform_photo_url(p, mode="detail") for p in raw_photos]

    is_favorite = False
    has_reported = False
    if user:
        fav_ids = get_user_favorite_ids(user["uid"])
        is_favorite = listing_id in fav_ids
        has_reported = has_user_reported(listing_id, user["uid"])

    can_view_reviewer = can_view_reviewer_details(user)

    return render_template(
        "listings/detail.html",
        listing=listing,
        detail_photos=detail_photos,
        is_favorite=is_favorite,
        has_reported=has_reported,
        can_view_reviewer=can_view_reviewer,
    )


@listings_bp.route("/listings/new", methods=["GET", "POST"])
@login_required
@not_banned
def create():
    """5-Step Add Listing Wizard with Cloudinary signed uploads."""
    user = getattr(g, "user", None)
    if not can_create_listing(user):
        abort(403)

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        cleaned, errors = validate_listing_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        doc_id = create_listing(cleaned, user)
        flash("Listing created successfully!", "success")
        return jsonify({
            "status": "success",
            "listingId": doc_id,
            "redirect": url_for("listings.detail", listing_id=doc_id),
        }), 201

    app_config = get_app_config()
    return render_template(
        "listings/wizard.html",
        app_config=app_config,
        is_edit_mode=False,
        listing=None,
    )


@listings_bp.route("/listings/<listing_id>/edit", methods=["GET", "POST"])
@login_required
@not_banned
def edit(listing_id):
    """5-Step Edit Listing Wizard."""
    listing = get_listing_by_id(listing_id)
    if not listing:
        abort(404)

    user = getattr(g, "user", None)
    if not can_edit_listing(user, listing):
        abort(403)

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        cleaned, errors = validate_listing_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        success = update_listing(listing_id, cleaned, listing, user)
        if not success:
            return jsonify({"error": "Failed to update listing."}), 500

        flash("Listing updated successfully!", "success")
        return jsonify({
            "status": "success",
            "listingId": listing_id,
            "redirect": url_for("listings.detail", listing_id=listing_id),
        }), 200

    app_config = get_app_config()
    return render_template(
        "listings/wizard.html",
        app_config=app_config,
        is_edit_mode=True,
        listing=listing,
    )


@listings_bp.route("/listings/<listing_id>/archive", methods=["POST"])
@login_required
@not_banned
def archive(listing_id):
    """Soft-deletes / withdraws a listing by owner or admin."""
    listing = get_listing_by_id(listing_id)
    if not listing:
        abort(404)

    user = getattr(g, "user", None)
    if not can_archive_listing(user, listing):
        abort(403)

    success = archive_listing(listing_id)
    if success:
        flash("Listing was withdrawn and archived.", "info")
    else:
        flash("Failed to archive listing.", "error")

    return redirect(url_for("listings.my_listings"))


@listings_bp.route("/my-listings")
@login_required
@not_banned
def my_listings():
    """My Listings dashboard separated into Pending, Approved, and Rejected tabs."""
    user = getattr(g, "user", None)
    all_mine = fetch_my_listings(user["uid"])

    pending = [l for l in all_mine if l.get("status") == STATUS_PENDING and not l.get("isArchived")]
    approved = [l for l in all_mine if l.get("status") == STATUS_APPROVED and not l.get("isArchived")]
    rejected = [l for l in all_mine if l.get("status") == STATUS_REJECTED and not l.get("isArchived")]

    return render_template(
        "listings/my_listings.html",
        pending_listings=pending,
        approved_listings=approved,
        rejected_listings=rejected,
    )


@listings_bp.route("/favorites")
@login_required
@not_banned
def favorites():
    """Saved / favorited accommodation listings."""
    user = getattr(g, "user", None)
    fav_listings = fetch_favorite_listings(user["uid"])

    for item in fav_listings:
        if item.get("coverPhoto"):
            item["cardPhoto"] = transform_photo_url(item["coverPhoto"], mode="card")

    return render_template(
        "listings/favorites.html",
        listings=fav_listings,
    )


@listings_bp.route("/listings/<listing_id>/report", methods=["POST"])
@login_required
@not_banned
@limiter.limit("5 per minute")
def report(listing_id):
    """Submits a community issue report for an accommodation listing."""
    listing = get_listing_by_id(listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    user = getattr(g, "user", None)
    if not can_report_listing(user, listing):
        return jsonify({"error": "You cannot report this listing."}), 403

    if has_user_reported(listing_id, user["uid"]):
        return jsonify({"error": "You have already submitted a report for this listing."}), 400

    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()
    if len(reason) < 5:
        return jsonify({"error": "Please provide a descriptive reason (at least 5 characters)."}), 400

    success = submit_report(
        listing_id=listing_id,
        listing_title=listing.get("title", "Listing"),
        user_id=user["uid"],
        user_name=user.get("name", "User"),
        reason=reason,
    )

    if success:
        return jsonify({"status": "success", "message": "Report submitted for admin review."}), 201
    return jsonify({"error": "Failed to submit report. Please try again."}), 500
