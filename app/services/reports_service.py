"""
Community reports service:
Manages reports submitted to reports/{listingId}_{reportedBy}.
"""

import logging
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from .cache import read_counter
from ..extensions import get_firestore_client

logger = logging.getLogger(__name__)


def has_user_reported(listing_id: str, user_id: str) -> bool:
    """Checks whether user has already submitted a report for this listing."""
    if not listing_id or not user_id:
        return False
    report_id = f"{listing_id}_{user_id}"
    try:
        db = get_firestore_client()
        read_counter.increment(1)
        doc = db.collection("reports").document(report_id).get()
        return doc.exists
    except Exception as e:
        logger.error("Error checking report existence %s: %s", report_id, e)
        return False


def submit_report(
    listing_id: str,
    listing_title: str,
    user_id: str,
    user_name: str,
    reason: str,
) -> bool:
    """Submits a new community report with deterministic ID."""
    report_id = f"{listing_id}_{user_id}"
    try:
        db = get_firestore_client()
        db.collection("reports").document(report_id).set({
            "listingId": listing_id,
            "listingTitle": listing_title,
            "reportedBy": user_id,
            "reporterName": user_name,
            "reason": reason.strip(),
            "status": "open",
            "createdAt": SERVER_TIMESTAMP,
        })
        logger.info("Report %s submitted successfully", report_id)
        return True
    except Exception as e:
        logger.error("Failed to submit report %s: %s", report_id, e)
        return False
