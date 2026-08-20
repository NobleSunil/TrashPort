import logging
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    If the serviceAccountKey.json file is not found, it falls back to a warning
    (for local testing/mocking purposes).
    """
    if not firebase_admin._apps:
        credentials_path = getattr(settings, "FIREBASE_CREDENTIALS", None)
        if credentials_path:
            from pathlib import Path
            credentials_path = Path(credentials_path)
            if credentials_path.exists():
                try:
                    cred = credentials.Certificate(str(credentials_path))
                    firebase_admin.initialize_app(cred)
                    logger.info(f"Firebase Admin SDK successfully initialized from {credentials_path}.")
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase with certificate from {credentials_path}: {e}")
            else:
                logger.warning(
                    f"Firebase credentials file not found at {credentials_path}. "
                    "Running in Mock / Development Authentication mode."
                )
        else:
            logger.warning("FIREBASE_CREDENTIALS settings is not configured. Running in Mock / Development Authentication mode.")

