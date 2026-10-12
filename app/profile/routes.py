from flask import Blueprint, render_template, g
from ..auth.decorators import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    """User profile overview and management."""
    return render_template("profile/index.html", user=g.user)
