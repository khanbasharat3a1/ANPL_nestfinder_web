"""
Firestore accommodation listings service:
- Optimized Explore feed with signed cursor pagination & 90s TTL cache
- Single listing fetching
- Creation with Approver/SuperAdmin auto-approval
- Update with Approved -> Pending reset
- Archiving & My Listings tabs
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from ..constants import (
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_ARCHIVED,
    LISTINGS_PER_PAGE,
)
from .cache import explore_cache, read_counter
from .pagination import create_cursor_token, parse_cursor_token
from .policy import should_auto_approve_listing
from ..extensions import get_firestore_client

logger = logging.getLogger(__name__)


def serialize_doc(doc) -> dict[str, Any]:
    """Serializes a Firestore document snapshot into a Python dict."""
    data = doc.to_dict() or {}
    data["id"] = doc.id

    # Normalize timestamps
    for date_field in ("availableFrom", "reviewedAt", "createdAt", "updatedAt"):
        val = data.get(date_field)
        if hasattr(val, "isoformat"):
            data[date_field] = val.isoformat()
        elif hasattr(val, "to_datetime"):
            data[date_field] = val.to_datetime().isoformat()

    return data


def fetch_approved_listings(
    filters: Optional[dict[str, Any]] = None,
    cursor_token: Optional[str] = None,
    secret_key: str = "secret",
    limit: int = LISTINGS_PER_PAGE,
) -> dict[str, Any]:
    """
    Fetches approved and non-archived listings for the Explore feed.
    Enforces composite index compatibility from firestore.indexes.json.
    Caches results in memory for 90 seconds.
    """
    filters = filters or {}
    cache_key = f"explore:{sorted(filters.items())}:{cursor_token}:{limit}"
    cached = explore_cache.get(cache_key)
    if cached is not None:
        return cached

    db = get_firestore_client()
    if db is None:
        return {"listings": [], "hasMore": False, "nextCursor": None}

    query = (
        db.collection("listings")
        .where("status", "==", STATUS_APPROVED)
        .where("isArchived", "==", False)
    )

    # 1. Apply discrete Firestore equality filters
    ptype = filters.get("type")
    if ptype:
        query = query.where("type", "==", ptype)

    furnishing = filters.get("furnishing")
    if furnishing:
        query = query.where("furnishing", "==", furnishing)

    gender = filters.get("genderPreference")
    if gender:
        query = query.where("genderPreference", "==", gender)

    locality = filters.get("locality")
    if locality:
        query = query.where("locality", "==", locality)

    # 2. Ordering
    sort_by = filters.get("sortBy", "newest")
    if sort_by == "rentLowToHigh":
        sort_field = "rentPerMonth"
        query = query.order_by(sort_field, direction="ASCENDING")
    elif sort_by == "rentHighToLow":
        sort_field = "rentPerMonth"
        query = query.order_by(sort_field, direction="DESCENDING")
    else:
        sort_field = "createdAt"
        query = query.order_by(sort_field, direction="DESCENDING")

    # 3. Apply cursor token if provided
    if cursor_token:
        cursor_data = parse_cursor_token(cursor_token, secret_key)
        if cursor_data:
            cursor_doc = db.collection("listings").document(cursor_data["id"]).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)

    # Fetch limit + 1 to detect has_next_page
    fetch_limit = limit + 1
    query = query.limit(fetch_limit)

    try:
        docs = list(query.stream())
        read_counter.increment(len(docs))
    except Exception as e:
        logger.error("Error executing Explore query: %s", e)
        docs = []

    has_more = len(docs) > limit
    page_docs = docs[:limit]
    listings = [serialize_doc(d) for d in page_docs]

    # 4. Client-side search and rent range filtering
    min_rent = filters.get("minRent")
    max_rent = filters.get("maxRent")
    search_q = filters.get("searchQuery", "").strip().lower()

    if min_rent is not None:
        listings = [l for l in listings if float(l.get("rentPerMonth", 0)) >= float(min_rent)]
    if max_rent is not None:
        listings = [l for l in listings if float(l.get("rentPerMonth", 0)) <= float(max_rent)]
    if search_q:
        listings = [
            l for l in listings
            if (
                search_q in l.get("title", "").lower()
                or search_q in l.get("locality", "").lower()
                or search_q in l.get("fullAddress", "").lower()
                or search_q in l.get("description", "").lower()
            )
        ]

    # Generate next cursor token
    next_cursor = None
    if has_more and page_docs:
        last_doc = page_docs[-1]
        last_data = last_doc.to_dict() or {}
        raw_val = last_data.get(sort_field)
        sort_val = raw_val.isoformat() if hasattr(raw_val, "isoformat") else raw_val
        next_cursor = create_cursor_token(
            doc_id=last_doc.id,
            sort_field=sort_field,
            sort_value=sort_val,
            secret_key=secret_key,
        )

    result = {
        "listings": listings,
        "hasMore": has_more,
        "nextCursor": next_cursor,
    }

    explore_cache.set(cache_key, result, ttl=90)
    return result


def get_listing_by_id(listing_id: str) -> Optional[dict[str, Any]]:
    """Fetches a single listing document by ID."""
    if not listing_id:
        return None
    try:
        db = get_firestore_client()
        if db is None:
            return None
        read_counter.increment(1)
        doc = db.collection("listings").document(listing_id).get()
        if not doc.exists:
            return None
        return serialize_doc(doc)
    except Exception as e:
        logger.error("Error getting listing %s: %s", listing_id, e)
        return None


def create_listing(cleaned_data: dict[str, Any], current_user: dict[str, Any]) -> str:
    """
    Creates a new listing in listings/{listing_id}.
    Auto-approves if creator is Approver or Super Admin.
    """
    db = get_firestore_client()
    doc_ref = db.collection("listings").document()
    doc_id = doc_ref.id

    is_auto = should_auto_approve_listing(current_user)
    target_status = STATUS_APPROVED if is_auto else STATUS_PENDING
    now = datetime.now(timezone.utc)

    reviewer_role = "Approver" if current_user.get("role") == "approver" else "Super Admin"

    listing_record = {
        **cleaned_data,
        "ownerId": current_user["uid"],
        "status": target_status,
        "isArchived": False,
        "rejectionReason": None,
        "reviewedBy": current_user["uid"] if is_auto else None,
        "reviewedByName": current_user.get("name") if is_auto else None,
        "reviewedByRole": reviewer_role if is_auto else None,
        "reviewedAt": now if is_auto else None,
        "createdAt": now,
        "updatedAt": now,
    }

    doc_ref.set(listing_record)
    read_counter.increment(1)
    explore_cache.clear()
    logger.info("Created listing %s (status: %s, auto-approved: %s)", doc_id, target_status, is_auto)
    return doc_id


def update_listing(
    listing_id: str,
    cleaned_data: dict[str, Any],
    existing_listing: dict[str, Any],
    current_user: dict[str, Any],
) -> bool:
    """
    Updates an existing accommodation listing.
    If listing was approved, editing key details resets status to pending.
    """
    try:
        db = get_firestore_client()
        was_approved = existing_listing.get("status") == STATUS_APPROVED
        is_admin = current_user.get("role") == "super_admin"

        target_status = STATUS_PENDING if (was_approved and not is_admin) else existing_listing.get("status")

        now = datetime.now(timezone.utc)
        updates = {
            **cleaned_data,
            "status": target_status,
            "rejectionReason": None,  # Cleared on resubmit
            "isArchived": False,
            "updatedAt": now,
        }

        db.collection("listings").document(listing_id).update(updates)
        explore_cache.clear()
        logger.info("Updated listing %s (target status: %s)", listing_id, target_status)
        return True
    except Exception as e:
        logger.error("Failed to update listing %s: %s", listing_id, e)
        return False


def archive_listing(listing_id: str) -> bool:
    """Soft-deletes / archives a listing."""
    try:
        db = get_firestore_client()
        db.collection("listings").document(listing_id).update({
            "status": STATUS_ARCHIVED,
            "isArchived": True,
            "updatedAt": SERVER_TIMESTAMP,
        })
        explore_cache.clear()
        logger.info("Archived listing %s", listing_id)
        return True
    except Exception as e:
        logger.error("Failed to archive listing %s: %s", listing_id, e)
        return False


def fetch_my_listings(user_id: str, status_filter: Optional[str] = None) -> list[dict[str, Any]]:
    """Fetches all listings owned by the given user, ordered by createdAt DESC."""
    try:
        db = get_firestore_client()
        if db is None:
            return []
        query = db.collection("listings").where("ownerId", "==", user_id)
        docs = list(query.stream())
        read_counter.increment(len(docs))

        listings = [serialize_doc(d) for d in docs]
        # Sort descending by createdAt
        listings.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)

        if status_filter:
            listings = [l for l in listings if l.get("status") == status_filter and not l.get("isArchived")]
        return listings
    except Exception as e:
        logger.error("Error fetching my listings for %s: %s", user_id, e)
        return []
