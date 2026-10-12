import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
basedir = Path(__file__).resolve().parent.parent
load_dotenv(basedir / ".env")


class Config:
    """Base application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-must-be-changed-in-production")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

    # Firebase Backend Service Account
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "atomic-north-accommodation-hub")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    # Firebase Web Client SDK Configuration (Exposed to browser JS)
    FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "")
    FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "atomic-north-accommodation-hub.firebaseapp.com")
    FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID", "1:758327271700:web:nestfinderweb001")
    FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "758327271700")

    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "khan-developers")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_SIGNED_PRESET = os.getenv("CLOUDINARY_SIGNED_PRESET", "accommodation_signed")

    # Session & Security
    SESSION_COOKIE_DAYS = int(os.getenv("SESSION_COOKIE_DAYS", "5"))
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 86400 * 5  # 5 days to match session cookie
    RATELIMIT_DEFAULT = "200/hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Talisman default
    TALISMAN_FORCE_HTTPS = False


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    TALISMAN_FORCE_HTTPS = False


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    TALISMAN_FORCE_HTTPS = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    TALISMAN_FORCE_HTTPS = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
