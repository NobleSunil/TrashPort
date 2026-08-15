from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminsConfig(AppConfig):
    name = "trashport.admins"
    verbose_name = _("Admins")
