from flask import Blueprint, render_template
from ..auth.decorators import role_required
from ..constants import ROLE_SUPER_ADMIN
from ..services.cache import read_counter

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@role_required(ROLE_SUPER_ADMIN)
def home():
    """Admin dashboard home showing metrics, read usage, and management tools."""
    reads_today = read_counter.get_count()
    return render_template("admin/home.html", reads_today=reads_today)
