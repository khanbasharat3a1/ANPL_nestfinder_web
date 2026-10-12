"""
NestFinder Authorization Policy Engine.
Pure functions, deny-by-default, no side-effects.
Single source of truth for authorization across the application.
"""

from typing import Any, Optional, Set
from ..constants import (
    ROLE_USER,
    ROLE_APPROVER,
    ROLE_SUPER_ADMIN,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_ARCHIVED,
    VALID_ROLES,
)

# Minor edit fields allowed for approvers during review
ALLOWED_MINOR_EDIT_FIELDS: Set[str] = {
    "title",
    "description",
    "amenities",
    "locality",
    "localityIsCustom",
    "distanceFromOfficeKm",
}


# ---------------------------------------------------------------------------
# Identity & Role Helpers
# ---------------------------------------------------------------------------

def is_authenticated(user: Optional[dict[str, Any]]) -> bool:
    """Checks whether the user object has a valid authenticated UID."""
    return bool(user and user.get("uid"))


def is_banned(user: Optional[dict[str, Any]]) -> bool:
    """Returns True if the user account is marked as banned."""
    return bool(user and user.get("isBanned") is True)


def is_active_user(user: Optional[dict[str, Any]]) -> bool:
    """Returns True if user is authenticated and not banned."""
    return is_authenticated(user) and not is_banned(user)


def get_user_role(user: Optional[dict[str, Any]]) -> str:
    """Extracts role string, defaulting to anonymous or user."""
    if not user:
        return "anonymous"
    return user.get("role", ROLE_USER)


def is_super_admin(user: Optional[dict[str, Any]]) -> bool:
    """Checks if user has super_admin privileges and is not banned."""
    return is_active_user(user) and user.get("role") == ROLE_SUPER_ADMIN


def is_approver(user: Optional[dict[str, Any]]) -> bool:
    """Checks if user is an approver or super_admin and is not banned."""
    return is_active_user(user) and user.get("role") in (ROLE_APPROVER, ROLE_SUPER_ADMIN)


def is_owner(user: Optional[dict[str, Any]], owner_id: Optional[str]) -> bool:
    """Checks if the authenticated user is the resource owner."""
    if not is_authenticated(user) or not owner_id:
        return False
    return user.get("uid") == owner_id


# ---------------------------------------------------------------------------
# Listing Policies
# ---------------------------------------------------------------------------

def can_view_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Determines if user can view a specific listing.
    - Approvers and super admins can view any listing.
    - Owners can view their own listings in any status.
    - Normal users / guests can only view approved, non-archived listings.
    - Banned users cannot view anything.
    """
    if not listing:
        return False
    if is_banned(user):
        return False
    if is_approver(user):
        return True
    if is_owner(user, listing.get("ownerId")):
        return True

    # Public visibility
    return (
        listing.get("status") == STATUS_APPROVED
        and not listing.get("isArchived", False)
    )


def can_create_listing(user: Optional[dict[str, Any]]) -> bool:
    """Any non-banned signed-in user can create a listing."""
    return is_active_user(user)


def should_auto_approve_listing(user: Optional[dict[str, Any]]) -> bool:
    """
    Listings created by approvers or super admins are auto-approved.
    """
    return is_approver(user)


def can_edit_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Determines if user can edit a listing:
    - Super admins can edit any listing.
    - Non-banned owners can edit if status is pending, rejected, or approved (editing an approved
      listing resets it to pending).
    - Archived listings cannot be edited by the owner.
    """
    if not listing or not is_active_user(user):
        return False
    if is_super_admin(user):
        return True
    if is_owner(user, listing.get("ownerId")):
        if listing.get("isArchived", False):
            return False
        return listing.get("status") in (STATUS_PENDING, STATUS_REJECTED, STATUS_APPROVED)
    return False


def can_archive_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Determines if user can soft-delete / archive a listing:
    - Super admins can archive any listing.
    - Non-banned owners can archive their own non-archived listings.
    """
    if not listing or not is_active_user(user):
        return False
    if is_super_admin(user):
        return True
    if is_owner(user, listing.get("ownerId")):
        return not listing.get("isArchived", False)
    return False


def can_unarchive_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """Only super_admin can unarchive a listing."""
    if not listing or not is_super_admin(user):
        return False
    return bool(listing.get("isArchived", False))


def can_delete_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """Only super_admin can permanently delete a listing."""
    return is_super_admin(user) and bool(listing)


# ---------------------------------------------------------------------------
# Reviewer Policies
# ---------------------------------------------------------------------------

def can_access_review_queue(user: Optional[dict[str, Any]]) -> bool:
    """Only approvers and super admins can access the review queue."""
    return is_approver(user)


def can_review_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Determines if user can approve or reject a listing:
    - Must be an approver or super admin.
    - Listing must be pending and not archived.
    - Approvers CANNOT review their own listing. Super admin can review any listing.
    """
    if not listing or not is_approver(user):
        return False
    if listing.get("status") != STATUS_PENDING or listing.get("isArchived", False):
        return False
    if is_super_admin(user):
        return True
    # Approver cannot review their own listing
    return listing.get("ownerId") != user.get("uid")


def can_minor_edit_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Determines if user can perform minor edits before approval.
    Follows same permission check as can_review_listing.
    """
    return can_review_listing(user, listing)


def allowed_minor_edit_fields() -> Set[str]:
    """Returns immutable set of field keys that approvers are permitted to edit."""
    return set(ALLOWED_MINOR_EDIT_FIELDS)


def can_view_reviewer_details(user: Optional[dict[str, Any]]) -> bool:
    """Only approvers and super admins can view who approved or rejected a listing."""
    return is_approver(user)


# ---------------------------------------------------------------------------
# Interaction Policies (Favorites, Reports)
# ---------------------------------------------------------------------------

def can_favorite_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """Any non-banned authenticated user can bookmark a listing they can view."""
    return is_active_user(user) and can_view_listing(user, listing)


def can_report_listing(user: Optional[dict[str, Any]], listing: Optional[dict[str, Any]]) -> bool:
    """
    Users can report listings:
    - Must be authenticated and not banned.
    - Cannot report their own listing.
    - Listing must be viewable.
    """
    if not listing or not is_active_user(user):
        return False
    if is_owner(user, listing.get("ownerId")):
        return False
    return can_view_listing(user, listing)


# ---------------------------------------------------------------------------
# Administration & Super Admin Policies
# ---------------------------------------------------------------------------

def can_manage_users(user: Optional[dict[str, Any]]) -> bool:
    """Super admins can access the user management console."""
    return is_super_admin(user)


def can_change_user_role(
    actor: Optional[dict[str, Any]],
    target_user: Optional[dict[str, Any]],
    new_role: str,
    super_admin_count: int,
) -> bool:
    """
    Rules for updating user roles:
    - Actor must be super_admin.
    - Actor cannot modify their own role.
    - new_role must be a valid role.
    - If target_user is a super_admin and new_role != super_admin, super_admin_count must be > 1.
    """
    if not is_super_admin(actor) or not target_user:
        return False
    if actor.get("uid") == target_user.get("uid"):
        return False
    if new_role not in VALID_ROLES:
        return False
    if target_user.get("role") == ROLE_SUPER_ADMIN and new_role != ROLE_SUPER_ADMIN:
        if super_admin_count <= 1:
            return False
    return True


def can_ban_user(
    actor: Optional[dict[str, Any]],
    target_user: Optional[dict[str, Any]],
    super_admin_count: int,
) -> bool:
    """
    Rules for banning users:
    - Actor must be super_admin.
    - Actor cannot ban themselves.
    - Cannot ban the last remaining super_admin.
    """
    if not is_super_admin(actor) or not target_user:
        return False
    if actor.get("uid") == target_user.get("uid"):
        return False
    if target_user.get("role") == ROLE_SUPER_ADMIN and super_admin_count <= 1:
        return False
    return True


def can_unban_user(
    actor: Optional[dict[str, Any]],
    target_user: Optional[dict[str, Any]],
) -> bool:
    """
    Rules for unbanning users:
    - Actor must be super_admin.
    - Actor cannot unban themselves.
    """
    if not is_super_admin(actor) or not target_user:
        return False
    if actor.get("uid") == target_user.get("uid"):
        return False
    return True


def can_manage_reports(user: Optional[dict[str, Any]]) -> bool:
    """Super admins can view, dismiss, or takedown community reports."""
    return is_super_admin(user)


def can_manage_config(user: Optional[dict[str, Any]]) -> bool:
    """Super admins can edit application settings (config/app)."""
    return is_super_admin(user)


def can_view_audit_logs(user: Optional[dict[str, Any]]) -> bool:
    """Super admins can inspect the immutable audit log."""
    return is_super_admin(user)


def can_bulk_action(user: Optional[dict[str, Any]], count: int) -> bool:
    """Bulk listing actions are restricted to super admins with max 50 items."""
    return is_super_admin(user) and 0 < count <= 50
