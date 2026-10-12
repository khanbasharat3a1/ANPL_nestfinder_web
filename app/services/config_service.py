"""
App configuration service with 5-minute in-memory caching.
Fetches config/app or falls back to system defaults.
"""

import logging
from typing import Any
from ..constants import (
    DEFAULT_LOCALITIES,
    DEFAULT_AMENITIES,
    DEFAULT_PROPERTY_TYPE_LABELS,
    OFFICE_NAME,
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_ADDRESS,
)
from .cache import config_cache, read_counter
from ..extensions import get_firestore_client

logger = logging.getLogger(__name__)

CONFIG_DOC_ID = "app"


def get_default_config() -> dict[str, Any]:
    """Returns fallback configuration defaults matching app_config.dart."""
    return {
        "localities": list(DEFAULT_LOCALITIES),
        "amenities": list(DEFAULT_AMENITIES),
        "officeName": OFFICE_NAME,
        "officeLatitude": OFFICE_LATITUDE,
        "officeLongitude": OFFICE_LONGITUDE,
        "officeAddress": OFFICE_ADDRESS,
        "propertyTypeLabels": dict(DEFAULT_PROPERTY_TYPE_LABELS),
        "propertyTypeEnabled": {k: True for k in DEFAULT_PROPERTY_TYPE_LABELS},
    }


def get_app_config(bypass_cache: bool = False) -> dict[str, Any]:
    """
    Fetches config/app document from Firestore with 5-minute TTL in-memory caching.
    """
    cache_key = "config_app"
    if not bypass_cache:
        cached = config_cache.get(cache_key)
        if cached is not None:
            return cached

    defaults = get_default_config()
    try:
        db = get_firestore_client()
        if db is None:
            config_cache.set(cache_key, defaults, ttl=300)
            return defaults
        read_counter.increment(1)
        doc = db.collection("config").document(CONFIG_DOC_ID).get()
        if not doc.exists:
            config_cache.set(cache_key, defaults, ttl=300)
            return defaults

        data = doc.to_dict() or {}
        merged = {
            "localities": data.get("localities") or defaults["localities"],
            "amenities": data.get("amenities") or defaults["amenities"],
            "officeName": data.get("officeName") or defaults["officeName"],
            "officeLatitude": float(data.get("officeLatitude", defaults["officeLatitude"])),
            "officeLongitude": float(data.get("officeLongitude", defaults["officeLongitude"])),
            "officeAddress": data.get("officeAddress", defaults["officeAddress"]),
            "propertyTypeLabels": data.get("propertyTypeLabels") or defaults["propertyTypeLabels"],
            "propertyTypeEnabled": data.get("propertyTypeEnabled") or defaults["propertyTypeEnabled"],
        }
        config_cache.set(cache_key, merged, ttl=300)
        return merged
    except Exception as e:
        logger.error("Error reading config/app: %s", e)
        return defaults


def update_app_config(new_config: dict[str, Any]) -> bool:
    """Updates config/app in Firestore and invalidates cache."""
    try:
        db = get_firestore_client()
        db.collection("config").document(CONFIG_DOC_ID).set(new_config, merge=True)
        config_cache.delete("config_app")
        return True
    except Exception as e:
        logger.error("Error updating config/app: %s", e)
        return False
