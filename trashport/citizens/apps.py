from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CitizensConfig(AppConfig):
    name = "trashport.citizens"
    verbose_name = _("Citizens")
