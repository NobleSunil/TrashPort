from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MapsConfig(AppConfig):
    name = "trashport.maps"
    verbose_name = _("Maps & Geo-Tracking")
