import logging
from django.dispatch import Signal, receiver

logger = logging.getLogger(__name__)

# Custom Firebase Signals
firebase_user_authenticated = Signal()
firebase_user_registered = Signal()


@receiver(firebase_user_authenticated)
def handle_firebase_user_login(sender, user, decoded_token, **kwargs):
    logger.info(f"Firebase signal: User {user.email} authenticated via UID {decoded_token.get('uid')}")
