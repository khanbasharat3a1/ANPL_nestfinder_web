from datetime import datetime
from app.listings.validators import clean_phone_number, validate_listing_payload


def test_clean_phone_number():
    assert clean_phone_number("9876543210") == "9876543210"
    assert clean_phone_number("+91 9876543210") == "9876543210"
    assert clean_phone_number("91-9876543210") == "9876543210"
    assert clean_phone_number("88888-88888") == "8888888888"
    assert clean_phone_number("5123456789") is None  # Doesn't start with 6-9
    assert clean_phone_number("12345") is None
    assert clean_phone_number("") is None
    assert clean_phone_number(None) is None


def test_validate_listing_payload_valid():
    valid_data = {
        "title": "Sunlit 2BHK Apartment",
        "description": "Spacious flat near Billawar Market, power backup included.",
        "type": "flat",
        "rentPerMonth": 6500,
        "securityDeposit": 6500,
        "furnishing": "semi",
        "bedrooms": 2,
        "bathrooms": 1,
        "genderPreference": "any",
        "availableFrom": "2026-11-01",
        "locality": "Billawar Main Bazar",
        "localityIsCustom": False,
        "fullAddress": "Near Shiva Temple, Main Bazar, Billawar",
        "amenities": ["WiFi", "Power Backup"],
        "photos": [
            "https://res.cloudinary.com/khan-developers/image/upload/v1/listings/u1/photo1.jpg",
            "https://res.cloudinary.com/khan-developers/image/upload/v1/listings/u1/photo2.jpg",
        ],
        "ownerPhone": "+91 9876543210",
        "whatsappNumber": "9876543210",
        "ownerName": "Aman Sharma",
        "distanceFromOfficeKm": 2.5,
    }

    cleaned, errors = validate_listing_payload(valid_data)
    assert not errors
    assert cleaned is not None
    assert cleaned["title"] == "Sunlit 2BHK Apartment"
    assert cleaned["rentPerMonth"] == 6500.0
    assert cleaned["coverPhoto"] == valid_data["photos"][0]
    assert cleaned["ownerPhone"] == "9876543210"
    assert isinstance(cleaned["availableFrom"], datetime)


def test_validate_listing_payload_invalid():
    invalid_data = {
        "title": "Tiny",  # < 5 chars
        "description": "Too short",  # < 10 chars
        "type": "villa",  # invalid enum
        "rentPerMonth": -500,  # <= 0
        "securityDeposit": -10,  # < 0
        "furnishing": "luxury",  # invalid
        "bedrooms": -1,
        "bathrooms": 0,
        "genderPreference": "couples",  # invalid
        "availableFrom": "not-a-date",
        "locality": "A" * 70,  # > 60 chars
        "fullAddress": "Hi",  # < 5 chars
        "photos": ["https://evil.com/fake.jpg"],  # non-cloudinary and < 2 photos
        "ownerPhone": "12345",  # invalid phone
        "ownerName": "",
    }

    cleaned, errors = validate_listing_payload(invalid_data)
    assert cleaned is None
    assert "title" in errors
    assert "description" in errors
    assert "type" in errors
    assert "rentPerMonth" in errors
    assert "securityDeposit" in errors
    assert "furnishing" in errors
    assert "bedrooms" in errors
    assert "bathrooms" in errors
    assert "genderPreference" in errors
    assert "availableFrom" in errors
    assert "locality" in errors
    assert "fullAddress" in errors
    assert "photos" in errors
    assert "ownerPhone" in errors
    assert "ownerName" in errors
