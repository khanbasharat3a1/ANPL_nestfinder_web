import logging
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
)
from ..auth.decorators import login_required, not_banned
from ..services.users_service import update_profile
from ..services.notifications_service import fetch_user_notifications
from ..listings.validators import clean_phone_number

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    """User profile overview."""
    return render_template("profile/index.html", user=g.user)


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
@not_banned
def edit():
    """Edit user name and phone number."""
    user = g.user
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw_phone = request.form.get("phone", "").strip()

        if not (1 <= len(name) <= 100):
            flash("Name must be between 1 and 100 characters.", "error")
            return render_template("profile/edit.html", user=user)

        phone = None
        if raw_phone:
            phone = clean_phone_number(raw_phone)
            if not phone:
                flash("Please enter a valid 10-digit Indian mobile number.", "error")
                return render_template("profile/edit.html", user=user)

        success = update_profile(user["uid"], name=name, phone=phone)
        if success:
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile.index"))
        else:
            flash("Failed to update profile. Please try again.", "error")

    return render_template("profile/edit.html", user=user)


@profile_bp.route("/notifications")
@login_required
def notifications():
    """In-app notifications feed."""
    user = g.user
    notifs = fetch_user_notifications(user["uid"])
    return render_template("profile/notifications.html", notifications=notifs)
