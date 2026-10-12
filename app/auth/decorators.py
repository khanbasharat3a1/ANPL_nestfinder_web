from functools import wraps
from flask import g, request, redirect, url_for, abort, jsonify


def login_required(f):
    """Ensures user is authenticated with a valid session cookie."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "user", None):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
            return redirect(url_for("auth.login", next=request.full_path))
        return f(*args, **kwargs)
    return decorated_function


def not_banned(f):
    """Ensures authenticated user is not banned."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(g, "user", None)
        if user and user.get("isBanned"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Forbidden", "message": "Account suspended."}), 403
            return redirect(url_for("auth.banned"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Ensures user is logged in, not banned, and has one of the required roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "user", None)
            if not user:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized"}), 401
                return redirect(url_for("auth.login", next=request.full_path))

            if user.get("isBanned"):
                return redirect(url_for("auth.banned"))

            if user.get("role") not in roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden", "message": "Insufficient permissions."}), 403
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
