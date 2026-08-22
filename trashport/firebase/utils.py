import logging
from pathlib import Path
from django.conf import settings
import firebase_admin
from firebase_admin import auth, credentials
from .exceptions import FirebaseAuthenticationError

logger = logging.getLogger(__name__)


def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        cred_path = getattr(settings, "FIREBASE_CREDENTIALS", None)
        if cred_path:
            path_obj = Path(cred_path)
            if path_obj.exists():
                try:
                    cred = credentials.Certificate(str(path_obj))
                    firebase_admin.initialize_app(cred)
                    logger.info(f"Firebase Admin SDK initialized with {path_obj}")
                    return
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase credentials: {e}")
        logger.warning("Firebase credentials not configured or file not found. Running in dev fallback mode.")


def verify_firebase_id_token(token: str, check_revoked: bool = False) -> dict:
    """Verifies Firebase ID token or accepts mock tokens in development/testing."""
    if not token:
        raise FirebaseAuthenticationError("Token is required.")

    if token.startswith("mock-token-"):
        uid = token.replace("mock-token-", "")
        return {
            "uid": uid,
            "email": f"{uid}@trashport.local",
            "name": uid.capitalize(),
            "is_mock": True,
        }

    initialize_firebase()
    try:
        return auth.verify_id_token(token, check_revoked=check_revoked, clock_skew_seconds=60)
    except Exception as e:
        raise FirebaseAuthenticationError(f"Firebase token verification failed: {str(e)}") from e
