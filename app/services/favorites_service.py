"""
User favorites management:
Manages subcollection at users/{uid}/favorites/{listingId}.
"""

import logging
from typing import Any
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from google.cloud.firestore_v1.field_path import FieldPath
from ..constants import STATUS_APPROVED
from .cache import read_counter
from .listings_service import serialize_doc
from ..extensions import get_firestore_client

logger = logging.getLogger(__name__)


def get_user_favorite_ids(user_id: str) -> set[str]:
    """Returns set of listing IDs favorited by the user."""
    if not user_id:
        return set()
    try:
        db = get_firestore_client()
        if db is None:
            return set()
        docs = list(db.collection("users").document(user_id).collection("favorites").stream())
        read_counter.increment(len(docs))
        return {d.id for d in docs}
    except Exception as e:
        logger.error("Error loading favorite IDs for %s: %s", user_id, e)
        return set()


def toggle_favorite(user_id: str, listing_id: str, should_favorite: bool) -> bool:
    """Toggles bookmark for a listing."""
    if not user_id or not listing_id:
        return False
    try:
        db = get_firestore_client()
        if db is None:
            return False
        doc_ref = db.collection("users").document(user_id).collection("favorites").document(listing_id)
        if should_favorite:
            doc_ref.set({
                "listingId": listing_id,
                "savedAt": SERVER_TIMESTAMP,
            })
        else:
            doc_ref.delete()
        return True
    except Exception as e:
        logger.error("Error toggling favorite for %s on %s: %s", user_id, listing_id, e)
        return False


def fetch_favorite_listings(user_id: str) -> list[dict[str, Any]]:
    """
    Fetches full listing objects for all favorited accommodations.
    Batches queries in chunks of <= 30 to comply with Firestore whereIn limits.
    """
    fav_ids = list(get_user_favorite_ids(user_id))
    if not fav_ids:
        return []

    db = get_firestore_client()
    if db is None:
        return []
    results = []

    # Chunk into sizes of 30
    chunk_size = 30
    for i in range(0, len(fav_ids), chunk_size):
        chunk = fav_ids[i:i + chunk_size]
        try:
            docs = list(
                db.collection("listings")
                .where(FieldPath.document_id(), "in", chunk)
                .stream()
            )
            read_counter.increment(len(docs))
            for doc in docs:
                listing = serialize_doc(doc)
                if listing.get("status") == STATUS_APPROVED and not listing.get("isArchived"):
                    results.add(listing) if hasattr(results, 'add') else results.append(listing)
        except Exception as e:
            logger.error("Error fetching chunk of favorite listings: %s", e)

    return results
