import logging
from django.utils.deprecation import MiddlewareMixin
from .utils import verify_firebase_id_token
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class FirebaseAuthenticationMiddleware(MiddlewareMixin):
    """
    Optional middleware to populate request.firebase_user if Bearer token is provided.
    """
    def process_request(self, request):
        request.firebase_decoded = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                decoded = verify_firebase_id_token(token)
                request.firebase_decoded = decoded
            except Exception as e:
                logger.debug(f"Firebase token middleware inspection: {e}")
