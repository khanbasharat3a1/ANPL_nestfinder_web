"""
Server-side listing payload validation.
Enforces strict boundaries, regex checks, and Cloudinary origin protection.
"""

import re
from datetime import datetime
from typing import Any
from ..constants import (
    VALID_PROPERTY_TYPES,
    VALID_FURNISHING,
    VALID_GENDER_PREFERENCES,
    MIN_PHOTOS_REQUIRED,
    MAX_PHOTOS_ALLOWED,
    MAX_LOCALITY_LENGTH,
)
from ..services.cloudinary_service import is_valid_cloudinary_url

INDIAN_PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")


def clean_phone_number(phone: Any) -> str | None:
    """
    Strips country code (+91), dashes, spaces, and validates 10-digit Indian phone.
    """
    if not phone or not isinstance(phone, str):
        return None

    # Remove all non-digit characters first
    digits = re.sub(r"\D", "", phone.strip())

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    if INDIAN_PHONE_REGEX.match(digits):
        return digits
    return None


def validate_listing_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """
    Validates listing payload for creation or updates.
    Returns: (cleaned_dict, errors_dict)
    """
    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    # 1. Title
    title = str(data.get("title", "")).strip()
    if not (5 <= len(title) <= 100):
        errors["title"] = "Title must be between 5 and 100 characters."
    else:
        cleaned["title"] = title

    # 2. Description
    desc = str(data.get("description", "")).strip()
    if not (10 <= len(desc) <= 2000):
        errors["description"] = "Description must be between 10 and 2000 characters."
    else:
        cleaned["description"] = desc

    # 3. Property Type
    ptype = str(data.get("type", "")).lower().strip()
    if ptype not in VALID_PROPERTY_TYPES:
        errors["type"] = f"Invalid property type. Must be one of: {', '.join(sorted(VALID_PROPERTY_TYPES))}."
    else:
        cleaned["type"] = ptype

    # 4. Rent per month
    try:
        rent = float(data.get("rentPerMonth", 0))
        if rent <= 0:
            errors["rentPerMonth"] = "Monthly rent must be greater than 0."
        else:
            cleaned["rentPerMonth"] = round(rent, 2)
    except (ValueError, TypeError):
        errors["rentPerMonth"] = "Rent per month must be a valid number."

    # 5. Security deposit
    try:
        deposit = float(data.get("securityDeposit", 0))
        if deposit < 0:
            errors["securityDeposit"] = "Security deposit cannot be negative."
        else:
            cleaned["securityDeposit"] = round(deposit, 2)
    except (ValueError, TypeError):
        errors["securityDeposit"] = "Security deposit must be a valid number."

    # 6. Furnishing
    furnishing = str(data.get("furnishing", "")).lower().strip()
    if furnishing not in VALID_FURNISHING:
        errors["furnishing"] = f"Invalid furnishing option. Allowed: {', '.join(sorted(VALID_FURNISHING))}."
    else:
        cleaned["furnishing"] = furnishing

    # 7. Bedrooms & Bathrooms
    try:
        bedrooms = int(data.get("bedrooms", 1))
        if bedrooms < 0:
            errors["bedrooms"] = "Bedrooms cannot be negative."
        else:
            cleaned["bedrooms"] = bedrooms
    except (ValueError, TypeError):
        errors["bedrooms"] = "Bedrooms must be an integer."

    try:
        bathrooms = int(data.get("bathrooms", 1))
        if bathrooms < 1:
            errors["bathrooms"] = "At least 1 bathroom is required."
        else:
            cleaned["bathrooms"] = bathrooms
    except (ValueError, TypeError):
        errors["bathrooms"] = "Bathrooms must be an integer."

    # 8. Gender Preference
    gender = str(data.get("genderPreference", "")).lower().strip()
    if gender not in VALID_GENDER_PREFERENCES:
        errors["genderPreference"] = f"Invalid gender preference. Allowed: {', '.join(sorted(VALID_GENDER_PREFERENCES))}."
    else:
        cleaned["genderPreference"] = gender

    # 9. Available From date
    raw_date = data.get("availableFrom")
    if not raw_date:
        errors["availableFrom"] = "Available from date is required."
    else:
        if isinstance(raw_date, datetime):
            cleaned["availableFrom"] = raw_date
        elif isinstance(raw_date, str):
            try:
                # Support YYYY-MM-DD or ISO formats
                cleaned["availableFrom"] = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                try:
                    cleaned["availableFrom"] = datetime.strptime(raw_date[:10], "%Y-%m-%d")
                except ValueError:
                    errors["availableFrom"] = "Invalid date format. Expected YYYY-MM-DD."
        else:
            errors["availableFrom"] = "Available from date is invalid."

    # 10. Locality (max 60 chars per Firestore rules)
    locality = str(data.get("locality", "")).strip()
    if not (1 <= len(locality) <= MAX_LOCALITY_LENGTH):
        errors["locality"] = f"Locality is required and cannot exceed {MAX_LOCALITY_LENGTH} characters."
    else:
        cleaned["locality"] = locality

    cleaned["localityIsCustom"] = bool(data.get("localityIsCustom", False))

    # 11. Full Address
    address = str(data.get("fullAddress", "")).strip()
    if not (5 <= len(address) <= 250):
        errors["fullAddress"] = "Address must be between 5 and 250 characters."
    else:
        cleaned["fullAddress"] = address

    # 12. Office Distance (Optional)
    raw_dist = data.get("distanceFromOfficeKm")
    if raw_dist not in (None, "", "null"):
        try:
            dist = float(raw_dist)
            cleaned["distanceFromOfficeKm"] = max(0.0, round(dist, 2))
        except (ValueError, TypeError):
            errors["distanceFromOfficeKm"] = "Distance must be a valid number."
    else:
        cleaned["distanceFromOfficeKm"] = None

    # 13. Coordinates (Optional)
    cleaned["lat"] = float(data["lat"]) if data.get("lat") not in (None, "") else None
    cleaned["lng"] = float(data["lng"]) if data.get("lng") not in (None, "") else None

    # 14. Amenities
    raw_amenities = data.get("amenities", [])
    if isinstance(raw_amenities, list):
        cleaned["amenities"] = [str(a).strip() for a in raw_amenities if str(a).strip()]
    else:
        cleaned["amenities"] = []

    # 15. Photos (2 to 8, strictly Cloudinary)
    raw_photos = data.get("photos", [])
    if not isinstance(raw_photos, list):
        errors["photos"] = "Photos must be provided as a list."
    else:
        valid_photos = []
        for p in raw_photos:
            p_str = str(p).strip()
            if is_valid_cloudinary_url(p_str):
                valid_photos.append(p_str)
            else:
                errors["photos"] = "All photos must originate from the verified Cloudinary account."
                break

        if "photos" not in errors:
            if not (MIN_PHOTOS_REQUIRED <= len(valid_photos) <= MAX_PHOTOS_ALLOWED):
                errors["photos"] = f"Please upload between {MIN_PHOTOS_REQUIRED} and {MAX_PHOTOS_ALLOWED} photos."
            else:
                cleaned["photos"] = valid_photos
                cleaned["coverPhoto"] = valid_photos[0]

    # 16. Contact Info
    owner_phone = clean_phone_number(data.get("ownerPhone"))
    if not owner_phone:
        errors["ownerPhone"] = "A valid 10-digit Indian phone number starting with 6-9 is required."
    else:
        cleaned["ownerPhone"] = owner_phone

    raw_whatsapp = data.get("whatsappNumber")
    if raw_whatsapp not in (None, ""):
        wa = clean_phone_number(raw_whatsapp)
        if not wa:
            errors["whatsappNumber"] = "WhatsApp number must be a valid 10-digit Indian mobile number."
        else:
            cleaned["whatsappNumber"] = wa
    else:
        cleaned["whatsappNumber"] = None

    owner_name = str(data.get("ownerName", "")).strip()
    if not (1 <= len(owner_name) <= 100):
        errors["ownerName"] = "Owner name is required."
    else:
        cleaned["ownerName"] = owner_name

    if errors:
        return None, errors
    return cleaned, {}
