from django.contrib import admin
from .models import ServiceZone, CollectorLocation


@admin.register(ServiceZone)
class ServiceZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "center_latitude", "center_longitude", "radius_km", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(CollectorLocation)
class CollectorLocationAdmin(admin.ModelAdmin):
    list_display = ("collector", "latitude", "longitude", "speed", "heading", "updated_at")
    search_fields = ("collector__email", "collector__name")
