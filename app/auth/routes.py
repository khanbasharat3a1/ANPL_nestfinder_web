import logging
from datetime import timedelta
from urllib.parse import urlparse, urljoin
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    current_app,
    make_response,
    g,
)
from ..extensions import limiter, get_firebase_auth
from ..services.users_service import sync_or_create_user
from ..constants import SUPPORT_EMAIL

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def is_safe_url(target: str) -> bool:
    """Validates that a redirect target URL is safe and relative to this host."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth_bp.route("/login", methods=["GET"])
def login():
    """Renders authentication page for Google Sign-In and Email/Password."""
    if getattr(g, "user", None):
        return redirect(url_for("listings.explore"))
    next_url = request.args.get("next", "")
    return render_template("auth/login.html", next_url=next_url)


@auth_bp.route("/register", methods=["GET"])
def register():
    """Renders new user registration page."""
    if getattr(g, "user", None):
        return redirect(url_for("listings.explore"))
    return render_template("auth/register.html")


@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password():
    """Renders password reset request page."""
    return render_template("auth/forgot_password.html")


@auth_bp.route("/session", methods=["POST"])
@limiter.limit("15 per minute")
def create_session():
    """
    Exchanges a client Firebase ID token for a secure HTTP-Only session cookie.
    Creates or synchronizes the Firestore users/{uid} document if first sign-in.
    """
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken")
    name = data.get("name")
    phone = data.get("phone")

    if not id_token:
        return jsonify({"error": "Missing ID token"}), 400

    try:
        auth_module = get_firebase_auth()
        # Verify the Firebase ID token
        decoded_claims = auth_module.verify_id_token(id_token)
        uid = decoded_claims["uid"]
        email = decoded_claims.get("email", "")
        token_name = decoded_claims.get("name") or name
        photo_url = decoded_claims.get("picture")

        # Sync or initialize user document in Firestore (Set-If-Not-Exists)
        user_doc = sync_or_create_user(
            uid=uid,
            email=email,
            name=token_name,
            phone=phone,
            photo_url=photo_url,
        )

        # Create session cookie (5 days)
        session_days = current_app.config.get("SESSION_COOKIE_DAYS", 5)
        expires_in = timedelta(days=session_days)
        session_cookie = auth_module.create_session_cookie(id_token, expires_in=expires_in)

        next_param = request.args.get("next") or data.get("next")
        redirect_url = next_param if is_safe_url(next_param) else url_for("listings.explore")

        response = make_response(
            jsonify({
                "status": "success",
                "redirect": redirect_url,
                "user": {
                    "uid": uid,
                    "name": user_doc.get("name"),
                    "role": user_doc.get("role"),
                    "isBanned": user_doc.get("isBanned"),
                },
            })
        )

        # Set session cookie with security flags
        secure_cookie = request.is_secure and not current_app.debug
        response.set_cookie(
            "session",
            session_cookie,
            max_age=int(expires_in.total_seconds()),
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
            path="/",
        )
        return response
    except Exception as e:
        logger.error("Session creation failed: %s", e)
        return jsonify({"error": "Authentication failed", "details": str(e)}), 401


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logs out user, clears session cookie, and revokes refresh tokens."""
    user = getattr(g, "user", None)
    if user and user.get("uid"):
        try:
            auth_module = get_firebase_auth()
            auth_module.revoke_refresh_tokens(user["uid"])
        except Exception as e:
            logger.warning("Error revoking refresh tokens on logout: %s", e)

    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie("session", path="/")
    return response


@auth_bp.route("/banned", methods=["GET"])
def banned():
    """Landing page for suspended accounts."""
    user = getattr(g, "user", None)
    return render_template(
        "errors/banned.html",
        user=user,
        support_email=SUPPORT_EMAIL,
    )
