import logging
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class FirebaseConfig(AppConfig):
    name = "trashport.services.firebase"
    verbose_name = _("Firebase Integration")

    def ready(self):
        from .utils import initialize_firebase
        try:
            initialize_firebase()
        except Exception as e:
            logger.warning(f"Firebase app initialization skipped or deferred: {e}")
        import trashport.services.firebase.signals  # noqa: F401
