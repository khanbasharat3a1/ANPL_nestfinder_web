from flask import Blueprint, render_template, redirect, url_for, g

listings_bp = Blueprint("listings", __name__)


@listings_bp.route("/")
def index():
    """Root entry point redirects to Explore feed."""
    return redirect(url_for("listings.explore"))


@listings_bp.route("/explore")
def explore():
    """Explore feed showing verified accommodation listings."""
    return render_template("listings/explore.html")
