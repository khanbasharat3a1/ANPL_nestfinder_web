import pytest
from app.services.policy import (
    is_authenticated,
    is_banned,
    is_active_user,
    get_user_role,
    is_super_admin,
    is_approver,
    is_owner,
    can_view_listing,
    can_create_listing,
    should_auto_approve_listing,
    can_edit_listing,
    can_archive_listing,
    can_unarchive_listing,
    can_delete_listing,
    can_access_review_queue,
    can_review_listing,
    can_minor_edit_listing,
    allowed_minor_edit_fields,
    can_view_reviewer_details,
    can_favorite_listing,
    can_report_listing,
    can_manage_users,
    can_change_user_role,
    can_ban_user,
    can_unban_user,
    can_manage_reports,
    can_manage_config,
    can_view_audit_logs,
    can_bulk_action,
)


@pytest.fixture
def normal_user():
    return {"uid": "user_1", "role": "user", "isBanned": False, "name": "Aman"}


@pytest.fixture
def approver_user():
    return {"uid": "approver_1", "role": "approver", "isBanned": False, "name": "Priya"}


@pytest.fixture
def super_admin_user():
    return {"uid": "admin_1", "role": "super_admin", "isBanned": False, "name": "Basharat"}


@pytest.fixture
def banned_user():
    return {"uid": "banned_1", "role": "user", "isBanned": True, "name": "Spammer"}


@pytest.fixture
def approved_listing():
    return {
        "id": "list_1",
        "ownerId": "user_1",
        "status": "approved",
        "isArchived": False,
        "title": "Cosy Flat",
    }


@pytest.fixture
def pending_listing():
    return {
        "id": "list_2",
        "ownerId": "user_1",
        "status": "pending",
        "isArchived": False,
        "title": "Pending Room",
    }


@pytest.fixture
def rejected_listing():
    return {
        "id": "list_3",
        "ownerId": "user_1",
        "status": "rejected",
        "isArchived": False,
        "title": "Rejected House",
    }


@pytest.fixture
def archived_listing():
    return {
        "id": "list_4",
        "ownerId": "user_1",
        "status": "archived",
        "isArchived": True,
        "title": "Archived Flat",
    }


# ---------------------------------------------------------------------------
# Identity & Role Tests
# ---------------------------------------------------------------------------

def test_identity_and_roles(normal_user, approver_user, super_admin_user, banned_user):
    assert is_authenticated(normal_user)
    assert not is_authenticated(None)
    assert not is_authenticated({})

    assert is_banned(banned_user)
    assert not is_banned(normal_user)

    assert is_active_user(normal_user)
    assert not is_active_user(banned_user)
    assert not is_active_user(None)

    assert get_user_role(None) == "anonymous"
    assert get_user_role(normal_user) == "user"
    assert get_user_role(approver_user) == "approver"
    assert get_user_role(super_admin_user) == "super_admin"

    assert is_approver(approver_user)
    assert is_approver(super_admin_user)
    assert not is_approver(normal_user)

    assert is_super_admin(super_admin_user)
    assert not is_super_admin(approver_user)
    assert not is_super_admin(normal_user)

    assert is_owner(normal_user, "user_1")
    assert not is_owner(normal_user, "user_2")
    assert not is_owner(None, "user_1")


# ---------------------------------------------------------------------------
# Listing View & Action Tests
# ---------------------------------------------------------------------------

def test_can_view_listing(normal_user, approver_user, super_admin_user, banned_user,
                          approved_listing, pending_listing, archived_listing):
    # Anonymous and normal user can view approved
    assert can_view_listing(None, approved_listing)
    assert can_view_listing(normal_user, approved_listing)

    # Anonymous and non-owner cannot view pending or archived
    other_user = {"uid": "other_2", "role": "user", "isBanned": False}
    assert not can_view_listing(None, pending_listing)
    assert not can_view_listing(other_user, pending_listing)
    assert not can_view_listing(other_user, archived_listing)

    # Owner can view own pending and archived
    assert can_view_listing(normal_user, pending_listing)
    assert can_view_listing(normal_user, archived_listing)

    # Approver and Super Admin can view all
    assert can_view_listing(approver_user, pending_listing)
    assert can_view_listing(super_admin_user, pending_listing)
    assert can_view_listing(super_admin_user, archived_listing)

    # Banned user cannot view anything
    assert not can_view_listing(banned_user, approved_listing)


def test_listing_lifecycle_policy(normal_user, approver_user, super_admin_user,
                                  approved_listing, pending_listing, rejected_listing, archived_listing):
    # Create listing
    assert can_create_listing(normal_user)
    assert not should_auto_approve_listing(normal_user)
    assert should_auto_approve_listing(approver_user)
    assert should_auto_approve_listing(super_admin_user)

    # Edit listing
    # Owner can edit pending, rejected, approved
    assert can_edit_listing(normal_user, pending_listing)
    assert can_edit_listing(normal_user, rejected_listing)
    assert can_edit_listing(normal_user, approved_listing)
    # Owner cannot edit archived
    assert not can_edit_listing(normal_user, archived_listing)

    # Other normal user cannot edit
    other_user = {"uid": "other_2", "role": "user", "isBanned": False}
    assert not can_edit_listing(other_user, approved_listing)

    # Super admin can edit any
    assert can_edit_listing(super_admin_user, archived_listing)

    # Archive / Soft-delete
    assert can_archive_listing(normal_user, approved_listing)
    assert not can_archive_listing(normal_user, archived_listing)
    assert can_archive_listing(super_admin_user, approved_listing)

    # Unarchive and Delete
    assert can_unarchive_listing(super_admin_user, archived_listing)
    assert not can_unarchive_listing(normal_user, archived_listing)
    assert can_delete_listing(super_admin_user, approved_listing)
    assert not can_delete_listing(normal_user, approved_listing)


# ---------------------------------------------------------------------------
# Review Queue & Reviewer Tests
# ---------------------------------------------------------------------------

def test_reviewer_permissions(normal_user, approver_user, super_admin_user, pending_listing, approved_listing):
    assert not can_access_review_queue(normal_user)
    assert can_access_review_queue(approver_user)
    assert can_access_review_queue(super_admin_user)

    # Approver reviewing another user's pending listing
    assert can_review_listing(approver_user, pending_listing)

    # Approver CANNOT review their own listing
    own_pending_listing = {
        "id": "list_own",
        "ownerId": approver_user["uid"],
        "status": "pending",
        "isArchived": False,
    }
    assert not can_review_listing(approver_user, own_pending_listing)

    # Super admin can review own or any listing
    admin_own_pending = {
        "id": "list_admin_own",
        "ownerId": super_admin_user["uid"],
        "status": "pending",
        "isArchived": False,
    }
    assert can_review_listing(super_admin_user, admin_own_pending)

    # Cannot review already approved listing
    assert not can_review_listing(approver_user, approved_listing)

    # Minor edit fields
    assert allowed_minor_edit_fields() == {
        "title",
        "description",
        "amenities",
        "locality",
        "localityIsCustom",
        "distanceFromOfficeKm",
    }
    assert can_minor_edit_listing(approver_user, pending_listing)
    assert not can_minor_edit_listing(approver_user, own_pending_listing)

    # Reviewer details visibility
    assert not can_view_reviewer_details(normal_user)
    assert can_view_reviewer_details(approver_user)
    assert can_view_reviewer_details(super_admin_user)


# ---------------------------------------------------------------------------
# Favorites & Reports Tests
# ---------------------------------------------------------------------------

def test_favorites_and_reports(normal_user, approved_listing, pending_listing):
    other_user = {"uid": "other_2", "role": "user", "isBanned": False}

    assert can_favorite_listing(other_user, approved_listing)
    assert not can_favorite_listing(other_user, pending_listing)

    # User cannot report own listing
    assert not can_report_listing(normal_user, approved_listing)
    # Other user can report approved listing
    assert can_report_listing(other_user, approved_listing)


# ---------------------------------------------------------------------------
# Super Admin & User Management Tests
# ---------------------------------------------------------------------------

def test_user_management_rules(super_admin_user, normal_user, approver_user):
    target_admin = {"uid": "admin_2", "role": "super_admin", "isBanned": False}

    assert can_manage_users(super_admin_user)
    assert not can_manage_users(approver_user)

    # Cannot modify own role
    assert not can_change_user_role(super_admin_user, super_admin_user, "approver", super_admin_count=2)

    # Can change normal user to approver
    assert can_change_user_role(super_admin_user, normal_user, "approver", super_admin_count=2)

    # Cannot demote last super admin
    assert not can_change_user_role(super_admin_user, target_admin, "user", super_admin_count=1)
    # Can demote super admin if more than one exists
    assert can_change_user_role(super_admin_user, target_admin, "user", super_admin_count=2)

    # Ban guards
    assert not can_ban_user(super_admin_user, super_admin_user, super_admin_count=2)
    assert not can_ban_user(super_admin_user, target_admin, super_admin_count=1)
    assert can_ban_user(super_admin_user, target_admin, super_admin_count=2)
    assert can_ban_user(super_admin_user, normal_user, super_admin_count=1)

    assert can_unban_user(super_admin_user, normal_user)
    assert not can_unban_user(super_admin_user, super_admin_user)

    # Administration scopes
    assert can_manage_reports(super_admin_user)
    assert can_manage_config(super_admin_user)
    assert can_view_audit_logs(super_admin_user)

    # Bulk action limit
    assert can_bulk_action(super_admin_user, 50)
    assert not can_bulk_action(super_admin_user, 51)
    assert not can_bulk_action(super_admin_user, 0)
    assert not can_bulk_action(approver_user, 10)
