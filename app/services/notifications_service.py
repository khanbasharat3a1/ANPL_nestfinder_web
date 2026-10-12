"""
Notifications service:
Manages in-app notifications at users/{uid}/notifications/{notificationId}.
"""

import logging
from typing import Any
from .cache import read_counter
from ..extensions import get_firestore_client

logger = logging.getLogger(__name__)


def fetch_user_notifications(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    """Fetches user notifications ordered newest first."""
    if not user_id:
        return []
    try:
        db = get_firestore_client()
        query = (
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .order_by("createdAt", direction="DESCENDING")
            .limit(limit)
        )
        docs = list(query.stream())
        read_counter.increment(len(docs))

        results = []
        for d in docs:
            data = d.to_dict() or {}
            data["id"] = d.id
            created_at = data.get("createdAt")
            if hasattr(created_at, "isoformat"):
                data["createdAt"] = created_at.isoformat()
            results.append(data)
        return results
    except Exception as e:
        logger.error("Error fetching notifications for %s: %s", user_id, e)
        return []


def get_unread_notification_count(user_id: str) -> int:
    """Returns aggregate count of unread notifications."""
    if not user_id:
        return 0
    try:
        db = get_firestore_client()
        query = (
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .where("read", "==", False)
        )
        count_query = query.count()
        results = count_query.get()
        return results[0][0].value
    except Exception as e:
        logger.error("Error getting unread notification count for %s: %s", user_id, e)
        return 0


def mark_notification_as_read(user_id: str, notification_id: str) -> bool:
    """Marks a single notification as read."""
    try:
        db = get_firestore_client()
        (
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .document(notification_id)
            .update({"read": True})
        )
        return True
    except Exception as e:
        logger.error("Failed to mark notification %s as read: %s", notification_id, e)
        return False


def mark_all_notifications_as_read(user_id: str) -> bool:
    """Marks all unread notifications as read using a batch."""
    try:
        db = get_firestore_client()
        unread_docs = list(
            db.collection("users")
            .document(user_id)
            .collection("notifications")
            .where("read", "==", False)
            .stream()
        )
        if not unread_docs:
            return True

        batch = db.batch()
        for doc in unread_docs:
            batch.update(doc.reference, {"read": True})
        batch.commit()
        return True
    except Exception as e:
        logger.error("Failed to mark all notifications as read for %s: %s", user_id, e)
        return False
