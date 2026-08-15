from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CollectorsConfig(AppConfig):
    name = "trashport.collectors"
    verbose_name = _("Collectors")
