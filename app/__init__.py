import os
import logging
from flask import Flask, g, request, redirect, url_for, render_template, jsonify
from .config import config_by_name
from .constants import APP_NAME, APP_TAGLINE, APP_VERSION, SUPPORT_EMAIL
from .extensions import csrf, limiter, talisman, init_firebase, get_firebase_auth
from .services.users_service import get_user_profile

logger = logging.getLogger(__name__)


def format_inr(val) -> str:
    """Formats numeric values into Indian numbering format (e.g. ₹1,23,456)."""
    if val is None:
        return "₹0"
    try:
        val = int(round(float(val)))
    except (ValueError, TypeError):
        return f"₹{val}"

    s = str(abs(val))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        formatted = ",".join(reversed(groups)) + "," + last3

    prefix = "-" if val < 0 else ""
    return f"₹{prefix}{formatted}"


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for NestFinder Web."""
    if not config_name:
        config_name = os.getenv("FLASK_ENV", os.getenv("ENVIRONMENT", "development"))

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize Extensions
    csrf.init_app(app)
    limiter.init_app(app)

    # Content Security Policy compatible with Firebase Auth & Cloudinary
    csp = {
        "default-src": "'self'",
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "https://www.gstatic.com",
            "https://apis.google.com",
            "https://identitytoolkit.googleapis.com",
            "https://*.firebaseapp.com",
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
        ],
        "connect-src": [
            "'self'",
            "https://*.googleapis.com",
            "https://*.firebaseio.com",
            "https://identitytoolkit.googleapis.com",
            "https://securetoken.googleapis.com",
            "https://api.cloudinary.com",
            "https://res.cloudinary.com",
        ],
        "img-src": [
            "'self'",
            "data:",
            "https://res.cloudinary.com",
            "https://lh3.googleusercontent.com",
            "https://*.googleusercontent.com",
        ],
        "frame-src": [
            "'self'",
            "https://*.firebaseapp.com",
            "https://accounts.google.com",
        ],
        "object-src": "'none'",
        "base-uri": "'self'",
    }

    force_https = app.config.get("TALISMAN_FORCE_HTTPS", False)
    talisman.init_app(
        app,
        content_security_policy=csp,
        force_https=force_https,
        frame_options="DENY",
        strict_transport_security=force_https,
        content_security_policy_nonce_in=["script-src"],
    )

    # Initialize Firebase SDK
    with app.app_context():
        init_firebase(app)

    # Custom Jinja filters
    app.jinja_env.filters["format_inr"] = format_inr

    # Global Authentication & Session Hook
    @app.before_request
    def load_authenticated_user():
        g.user = None
        session_cookie = request.cookies.get("session")
        if not session_cookie:
            return

        try:
            auth_module = get_firebase_auth()
            decoded_claims = auth_module.verify_session_cookie(
                session_cookie,
                check_revoked=True,
            )
            uid = decoded_claims.get("uid")
            if uid:
                user_doc = get_user_profile(uid)
                if user_doc:
                    g.user = user_doc

                    # Check ban status
                    if user_doc.get("isBanned"):
                        allowed_endpoints = {"auth.banned", "auth.logout", "static"}
                        if request.endpoint and request.endpoint not in allowed_endpoints:
                            return redirect(url_for("auth.banned"))
        except Exception:
            # Session expired or revoked
            g.user = None

    # Context Processors for Templates
    @app.context_processor
    def inject_global_template_context():
        return {
            "current_user": getattr(g, "user", None),
            "app_name": APP_NAME,
            "app_tagline": APP_TAGLINE,
            "app_version": APP_VERSION,
            "support_email": SUPPORT_EMAIL,
            "firebase_config": {
                "apiKey": app.config.get("FIREBASE_WEB_API_KEY"),
                "authDomain": app.config.get("FIREBASE_AUTH_DOMAIN"),
                "projectId": app.config.get("FIREBASE_PROJECT_ID"),
                "appId": app.config.get("FIREBASE_APP_ID"),
                "messagingSenderId": app.config.get("FIREBASE_MESSAGING_SENDER_ID"),
            },
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden", "message": "You do not have permission to access this resource."}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Not Found", "message": "Requested resource was not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Too Many Requests", "message": "Rate limit exceeded. Please try again later."}), 429
        return render_template("errors/500.html", error_message="Rate limit exceeded. Please slow down."), 429

    # Register Blueprints
    from .auth.routes import auth_bp
    from .listings.routes import listings_bp
    from .review.routes import review_bp
    from .admin.routes import admin_bp
    from .profile.routes import profile_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)

    return app
