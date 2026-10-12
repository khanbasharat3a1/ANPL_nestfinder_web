import pytest
from app import create_app, format_inr


@pytest.fixture
def app():
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_inr_formatting():
    assert format_inr(0) == "₹0"
    assert format_inr(500) == "₹500"
    assert format_inr(1500) == "₹1,500"
    assert format_inr(123456) == "₹1,23,456"
    assert format_inr(1234567) == "₹12,34,567"
    assert format_inr(None) == "₹0"


def test_healthz_endpoint(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["app"] == "NestFinder"
    assert data["version"] == "1.0.0"


def test_public_routes(client):
    # Root redirects to explore
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/explore" in resp.headers["Location"]

    # Explore feed is public
    resp = client.get("/explore")
    assert resp.status_code == 200
    assert b"Accommodation in Billawar" in resp.data

    # Login and register pages are public
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"Welcome Back" in resp.data

    resp = client.get("/auth/register")
    assert resp.status_code == 200
    assert b"Create Account" in resp.data


def test_protected_routes_unauthenticated_redirect(client):
    # Review queue requires authentication
    resp = client.get("/review/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

    # Admin home requires authentication
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

    # Profile requires authentication
    resp = client.get("/profile/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

    # Add listing wizard requires authentication
    resp = client.get("/listings/new")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

    # My listings requires authentication
    resp = client.get("/my-listings")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]

    # Favorites requires authentication
    resp = client.get("/favorites")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_stage2_authenticated_user_routes(app):
    """Verifies that an authenticated user can access wizard, my listings, favorites, and upload sign."""
    with app.test_client() as client:
        @app.before_request
        def mock_user():
            from flask import g
            g.user = {
                "uid": "test_user_stage2",
                "name": "Basharat Khan",
                "email": "khanbasharat@gmail.com",
                "role": "user",
                "isBanned": False,
            }

        # Access Add Listing Wizard
        resp = client.get("/listings/new")
        assert resp.status_code == 200
        assert b"Post Accommodation" in resp.data
        assert b"wizard-form" in resp.data

        # Access My Listings
        resp = client.get("/my-listings")
        assert resp.status_code == 200
        assert b"My Listings" in resp.data
        assert b"Pending Verification" in resp.data

        # Access Favorites
        resp = client.get("/favorites")
        assert resp.status_code == 200
        assert b"Saved Accommodations" in resp.data

        # Access Profile Edit
        resp = client.get("/profile/edit")
        assert resp.status_code == 200
        assert b"Edit Profile" in resp.data

        # Access Notifications
        resp = client.get("/profile/notifications")
        assert resp.status_code == 200
        assert b"Notifications" in resp.data

        # Upload signing endpoint
        resp = client.post("/api/uploads/sign", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "signature" in data
        assert "timestamp" in data
        assert data["uploadPreset"] == "accommodation_signed"
        assert data["folder"] == "listings/test_user_stage2"


def test_user_role_route_guards(app):
    """Verifies route authorization according to role in g.user."""
    # 1. Normal user
    with app.test_client() as client:
        @app.before_request
        def mock_user_auth():
            from flask import g
            g.user = {
                "uid": "test_user_1",
                "name": "Aman",
                "email": "aman@atomicnorth.com",
                "role": "user",
                "isBanned": False,
            }

        resp = client.get("/profile/")
        assert resp.status_code == 200

        # Review queue blocked with 403
        resp = client.get("/review/")
        assert resp.status_code == 403

        # Admin console blocked with 403
        resp = client.get("/admin/")
        assert resp.status_code == 403

    # 2. Approver user
    app_approver = create_app("testing")
    with app_approver.test_client() as client:
        @app_approver.before_request
        def mock_approver_auth():
            from flask import g
            g.user = {
                "uid": "test_appr_1",
                "name": "Priya",
                "email": "priya@atomicnorth.com",
                "role": "approver",
                "isBanned": False,
            }

        # Can access review queue
        resp = client.get("/review/")
        assert resp.status_code == 200
        assert b"Review Queue" in resp.data

        # Admin blocked with 403
        resp = client.get("/admin/")
        assert resp.status_code == 403

    # 3. Super Admin user
    app_admin = create_app("testing")
    with app_admin.test_client() as client:
        @app_admin.before_request
        def mock_admin_auth():
            from flask import g
            g.user = {
                "uid": "test_admin_1",
                "name": "Basharat",
                "email": "khanbasharat@gmail.com",
                "role": "super_admin",
                "isBanned": False,
            }

        # Can access review queue and admin
        resp = client.get("/review/")
        assert resp.status_code == 200

        resp = client.get("/admin/")
        assert resp.status_code == 200
        assert b"Admin Console" in resp.data

    # 4. Banned user
    app_banned = create_app("testing")
    with app_banned.test_client() as client:
        @app_banned.before_request
        def mock_banned_auth():
            from flask import g, request, redirect, url_for
            g.user = {
                "uid": "test_banned_1",
                "name": "Spammer",
                "email": "banned@atomicnorth.com",
                "role": "user",
                "isBanned": True,
            }
            if request.endpoint not in {"auth.banned", "auth.logout", "static"}:
                return redirect(url_for("auth.banned"))

        resp = client.get("/explore")
        assert resp.status_code == 302
        assert "/auth/banned" in resp.headers["Location"]

        resp = client.get("/auth/banned")
        assert resp.status_code == 200
        assert b"Account Suspended" in resp.data
