"""
Cloudinary integration service:
- Generates secure upload signatures (API secret remains server-side)
- Enforces Cloudinary origin URL constraints
- Builds image transformation URLs (w_400,c_fill,q_auto,f_auto and w_1080,c_limit,q_auto,f_auto)
- Best-effort image cleanup on listing deletion
"""

import time
import hashlib
import logging
import re
from typing import Any, Optional
from flask import current_app
from ..constants import CLOUDINARY_PREFIX

logger = logging.getLogger(__name__)


def is_valid_cloudinary_url(url: str) -> bool:
    """Strictly validates that an image URL originates from the designated Cloudinary account."""
    if not url or not isinstance(url, str):
        return False
    return url.startswith(CLOUDINARY_PREFIX)


def generate_upload_signature(uid: str) -> dict[str, Any]:
    """
    Generates an authenticated signature for signed Cloudinary uploads.
    Folder is strictly isolated to listings/<uid>.
    Uses the accommodation_signed preset.
    """
    api_key = current_app.config.get("CLOUDINARY_API_KEY", "")
    api_secret = current_app.config.get("CLOUDINARY_API_SECRET", "")
    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME", "khan-developers")
    preset = current_app.config.get("CLOUDINARY_SIGNED_PRESET", "accommodation_signed")

    timestamp = int(time.time())
    folder = f"listings/{uid}"

    # Parameters to sign in alphabetical order
    params_to_sign = {
        "folder": folder,
        "timestamp": timestamp,
        "upload_preset": preset,
    }

    # Cloudinary SHA-1 signature generation
    serialized = "&".join(f"{k}={params_to_sign[k]}" for k in sorted(params_to_sign.keys()))
    signature_input = f"{serialized}{api_secret}".encode("utf-8")
    signature = hashlib.sha1(signature_input).hexdigest()

    return {
        "cloudName": cloud_name,
        "apiKey": api_key,
        "timestamp": timestamp,
        "folder": folder,
        "uploadPreset": preset,
        "signature": signature,
    }


def transform_photo_url(url: str, mode: str = "card") -> str:
    """
    Injects Cloudinary transformation parameters into the photo URL.
    - card: w_400,c_fill,q_auto,f_auto
    - detail: w_1080,c_limit,q_auto,f_auto
    """
    if not url or not is_valid_cloudinary_url(url):
        return url or ""

    transform = "w_400,c_fill,q_auto,f_auto" if mode == "card" else "w_1080,c_limit,q_auto,f_auto"

    # Replace /image/upload/ with /image/upload/<transform>/
    needle = "/image/upload/"
    if needle in url:
        return url.replace(needle, f"{needle}{transform}/", 1)
    return url


def extract_public_id(url: str) -> Optional[str]:
    """Extracts Cloudinary public ID from URL for deletion."""
    try:
        # e.g., https://res.cloudinary.com/khan-developers/image/upload/v12345/listings/uid/sample.jpg
        match = re.search(r"/image/upload/(?:v\d+/)?(listings/[^.]+)", url)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None


def delete_listing_photos(photos: list[str]) -> None:
    """
    Best-effort deletion of images from Cloudinary upon permanent listing removal.
    """
    api_key = current_app.config.get("CLOUDINARY_API_KEY")
    api_secret = current_app.config.get("CLOUDINARY_API_SECRET")
    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME")

    if not api_key or not api_secret:
        logger.info("Cloudinary API credentials not configured; skipping photo deletion.")
        return

    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    for photo_url in photos:
        public_id = extract_public_id(photo_url)
        if public_id:
            try:
                res = cloudinary.uploader.destroy(public_id, invalidate=True)
                logger.info("Deleted Cloudinary image %s: %s", public_id, res)
            except Exception as e:
                logger.warning("Could not delete Cloudinary image %s: %s", public_id, e)
