"""
Application constants and configuration presets.
Mirrors core definitions in app_config.dart.
"""

# App Identity
APP_NAME = "NestFinder"
APP_TAGLINE = "Verified Accommodation for Atomic North"
COMPANY_NAME = "Atomic North Pvt Ltd"
COMPANY_LOCATION = "Billawar, Jammu & Kashmir"
SUPPORT_EMAIL = "khanbasharat@gmail.com"
APP_VERSION = "1.0.0"

# Timezone & Formatting
TIMEZONE = "Asia/Kolkata"
CURRENCY = "INR"

# Roles
ROLE_USER = "user"
ROLE_APPROVER = "approver"
ROLE_SUPER_ADMIN = "super_admin"
VALID_ROLES = {ROLE_USER, ROLE_APPROVER, ROLE_SUPER_ADMIN}

# Listing Statuses
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_ARCHIVED = "archived"
VALID_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_ARCHIVED}

# Accommodation Enums
VALID_PROPERTY_TYPES = {"flat", "house", "room", "pg", "hostel"}
VALID_FURNISHING = {"furnished", "semi", "unfurnished"}
VALID_GENDER_PREFERENCES = {"any", "male", "female"}

# Default Presets (Synced / Overridden by Firestore config/app)
DEFAULT_LOCALITIES = [
    "Billawar Main Bazar",
    "Mandli",
    "Dingi Simbli",
    "Phinter",
    "Kishanpur",
    "Dewal",
    "Durang",
]

DEFAULT_AMENITIES = [
    "WiFi",
    "24x7 Water Supply",
    "Power Backup",
    "Geyser / Hot Water",
    "Attached Bathroom",
    "Kitchen Access",
    "Parking (Bike)",
    "Parking (Car)",
    "RO Drinking Water",
    "Laundry / Washing Machine",
    "CCTV / Secure",
    "Meals Available",
]

DEFAULT_PROPERTY_TYPE_LABELS = {
    "flat": "Apartment / Flat",
    "house": "Independent House",
    "room": "Single Room",
    "pg": "Paying Guest (PG)",
    "hostel": "Hostel",
}

# Billawar Office Location Defaults
OFFICE_NAME = "Atomic North Campus, Billawar"
OFFICE_LATITUDE = 32.6105
OFFICE_LONGITUDE = 75.6027
OFFICE_ADDRESS = "Atomic North Campus, Billawar, Kathua, J&K - 184204"

# Limits & Storage
MIN_PHOTOS_REQUIRED = 2
MAX_PHOTOS_ALLOWED = 8
MAX_LOCALITY_LENGTH = 60
LISTINGS_PER_PAGE = 12
CLOUDINARY_PREFIX = "https://res.cloudinary.com/khan-developers/"
CLOUDINARY_FOLDER = "listings"
