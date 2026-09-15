"""
Django application configuration for core waste management.

Registers the waste_management domain models, signals, and admin configs.
"""

from django.apps import AppConfig


class WasteManagementConfig(AppConfig):
    """
    App configuration for core waste management operations,
    including pickups, categories, complaints, and wallet incentives.
    """
    name = "trashport.core.waste_management"
    verbose_name = "Core Waste Management"
