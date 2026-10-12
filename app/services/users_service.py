import logging
from datetime import datetime, timezone
from typing import Any, Optional
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from ..constants import ROLE_USER
from .cache import user_cache, read_counter
from ..extensions import get_firestore_client, get_firebase_auth

logger = logging.getLogger(__name__)


def get_user_profile(uid: str, bypass_cache: bool = False) -> Optional[dict[str, Any]]:
    """
    Retrieves user profile from Firestore users/{uid}.
    Utilizes a 60-second in-memory TTL cache to minimize Firestore reads.
    Enforces role and isBanned from Firestore as the single source of truth.
    """
    if not uid:
        return None

    if not bypass_cache:
        cached = user_cache.get(uid)
        if cached is not None:
            return cached

    try:
        db = get_firestore_client()
        read_counter.increment(1)
        doc = db.collection("users").document(uid).get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["uid"] = uid

        # Ensure defaults
        data.setdefault("role", ROLE_USER)
        data.setdefault("isBanned", False)
        data.setdefault("name", "Employee")
        data.setdefault("email", "")

        user_cache.set(uid, data, ttl=60)
        return data
    except Exception as e:
        logger.error("Error fetching user profile for %s: %s", uid, e)
        return None


def sync_or_create_user(
    uid: str,
    email: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    photo_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Ensures a users/{uid} document exists in Firestore (Set-If-Not-Exists).
    Never overwrites an existing user doc, role, or isBanned status.
    Mirrors Flutter AuthRepository._syncOrCreateUserDocument.
    """
    existing = get_user_profile(uid, bypass_cache=True)
    if existing:
        return existing

    display_name = (name or "Employee").strip()
    user_email = (email or "").strip()

    now = datetime.now(timezone.utc)
    new_user_data = {
        "name": display_name,
        "nameLower": display_name.lower(),
        "email": user_email,
        "emailLower": user_email.lower(),
        "phone": phone.strip() if phone else None,
        "photoUrl": photo_url,
        "role": ROLE_USER,
        "isBanned": False,
        "fcmToken": None,
        "createdAt": now,
    }

    try:
        db = get_firestore_client()
        # Set with merge to avoid overwriting existing fields if created concurrently
        db.collection("users").document(uid).set(new_user_data, merge=True)
        read_counter.increment(1)

        new_user_data["uid"] = uid
        user_cache.set(uid, new_user_data, ttl=60)
        logger.info("Successfully created new user document for uid=%s", uid)
        return new_user_data
    except Exception as e:
        logger.error("Error creating user doc for uid=%s: %s", uid, e)
        # Return fallback in-memory object
        new_user_data["uid"] = uid
        return new_user_data


def update_profile(
    uid: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    photo_url: Optional[str] = None,
) -> bool:
    """Updates user's profile information (name, phone, photoUrl)."""
    updates = {}
    if name is not None:
        trimmed_name = name.strip()
        updates["name"] = trimmed_name
        updates["nameLower"] = trimmed_name.lower()
    if phone is not None:
        updates["phone"] = phone.strip()
    if photo_url is not None:
        updates["photoUrl"] = photo_url.strip()

    if not updates:
        return True

    try:
        db = get_firestore_client()
        db.collection("users").document(uid).update(updates)
        user_cache.delete(uid)
        return True
    except Exception as e:
        logger.error("Failed to update profile for %s: %s", uid, e)
        return False


def set_user_role(uid: str, new_role: str) -> bool:
    """Updates role in Firestore and invalidates user cache."""
    try:
        db = get_firestore_client()
        db.collection("users").document(uid).update({"role": new_role})
        user_cache.delete(uid)
        return True
    except Exception as e:
        logger.error("Failed to update role for %s: %s", uid, e)
        return False


def set_user_ban_status(uid: str, is_banned: bool) -> bool:
    """Updates ban status in Firestore, invalidates cache, and revokes tokens if banned."""
    try:
        db = get_firestore_client()
        db.collection("users").document(uid).update({"isBanned": is_banned})
        user_cache.delete(uid)

        if is_banned:
            try:
                auth_module = get_firebase_auth()
                auth_module.revoke_refresh_tokens(uid)
                logger.info("Revoked Firebase refresh tokens for banned user %s", uid)
            except Exception as auth_err:
                logger.warning("Could not revoke refresh tokens for %s: %s", uid, auth_err)

        return True
    except Exception as e:
        logger.error("Failed to update ban status for %s: %s", uid, e)
        return False
