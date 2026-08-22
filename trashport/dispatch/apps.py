from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DispatchConfig(AppConfig):
    name = "trashport.dispatch"
    verbose_name = _("Automated Dispatch & Scheduling")
