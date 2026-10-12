from flask import Blueprint, render_template
from ..auth.decorators import role_required
from ..constants import ROLE_APPROVER, ROLE_SUPER_ADMIN

review_bp = Blueprint("review", __name__, url_prefix="/review")


@review_bp.route("/")
@role_required(ROLE_APPROVER, ROLE_SUPER_ADMIN)
def queue():
    """Review queue showing pending listings awaiting verification."""
    return render_template("review/queue.html")
