import json
import logging
import os
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

# Flask Extensions
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour"],
    storage_uri="memory://",
)
talisman = Talisman()

_firebase_initialized = False


def init_firebase(app=None) -> bool:
    """
    Initializes the firebase-admin SDK if not already initialized.
    Supports:
    1. GOOGLE_APPLICATION_CREDENTIALS file path
    2. FIREBASE_SERVICE_ACCOUNT_JSON raw JSON string (ideal for PaaS like Render)
    3. Fallback mock / project ID for local testing
    """
    global _firebase_initialized
    if _firebase_initialized or firebase_admin._apps:
        _firebase_initialized = True
        return True

    project_id = os.getenv("FIREBASE_PROJECT_ID", "atomic-north-accommodation-hub")
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    cred = None

    if service_account_json:
        try:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            logger.info("Initialized Firebase Admin via FIREBASE_SERVICE_ACCOUNT_JSON env string.")
        except Exception as e:
            logger.error("Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", e)

    elif service_account_path and os.path.isfile(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            logger.info("Initialized Firebase Admin via certificate file: %s", service_account_path)
        except Exception as e:
            logger.error("Failed to load GOOGLE_APPLICATION_CREDENTIALS (%s): %s", service_account_path, e)

    try:
        if cred:
            firebase_admin.initialize_app(cred, {"projectId": project_id})
        else:
            # Fallback initialization (uses Application Default Credentials if available)
            logger.warning("No explicit Firebase service account found. Using default credentials.")
            firebase_admin.initialize_app(options={"projectId": project_id})
        _firebase_initialized = True
        return True
    except Exception as e:
        logger.error("Firebase Admin initialization error: %s", e)
        return False


def get_firestore_client():
    """Returns Firestore client instance."""
    init_firebase()
    return firestore.client()


def get_firebase_auth():
    """Returns Firebase Auth module handle."""
    init_firebase()
    return auth
