"""
waste_management/admin.py — Django Admin Panel Registrations
=============================================================

PURPOSE:
  Registers all waste_management models into Django's /admin/ panel.
  Admins can browse, search, filter, and edit records directly from the
  built-in admin interface at settings.ADMIN_URL (default: /django-admin/).

  These registrations are for emergency data management and debugging only.
  Day-to-day admin operations use the custom AdminDashboardView UI instead.

MODELS REGISTERED:
  Address              : View citizen pickup addresses, filter by city/state.
  WasteCategory        : View/edit categories, pricing, and point rates.
  PickupRequest        : Full pickup history with status, payment, and collector filters.
  Complaint            : View and manage citizen complaints.
  CollectorPayoutSetting: View and edit collector payout formula settings.
  AnonymousFeedback    : Review anonymous feedback; mark as reviewed inline.

CONNECTION MAP:
  - waste_management/models.py → all model classes registered here
  - config/urls.py             → path(settings.ADMIN_URL, admin.site.urls)

IMPACT:
  - Modifying list_display changes which columns appear in the admin list view.
  - Adding list_editable allows inline editing (currently used for AnonymousFeedback.is_reviewed).
  - These admin classes do NOT affect the main TrashPort UI — only the /admin/ panel.
"""

from django.contrib import admin
from .models import Address, WasteCategory, PickupRequest, Complaint

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin configuration for citizen addresses and default pickup locations."""
    list_display = ["id", "user", "address_line1", "city", "state", "postal_code", "is_default"]
    list_filter = ["city", "state", "is_default"]
    search_fields = ["user__email", "address_line1", "city"]

@admin.register(WasteCategory)
class WasteCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for waste material categories, pricing rates, and incentive points."""
    list_display = ["id", "name", "fee_per_kg", "points_per_kg", "created_at"]
    search_fields = ["name"]

@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    """Admin configuration for inspecting, filtering, and debugging pickup request lifecycles."""
    list_display = ["id", "citizen", "collector", "category", "weight_kg", "fee", "points_earned", "is_paid", "status", "schedule_date"]
    list_filter = ["status", "is_paid", "category"]
    search_fields = ["citizen__email", "collector__email", "id"]

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """Admin configuration for viewing citizen complaint tickets and resolution statuses."""
    list_display = ["id", "citizen", "pickup_request", "title", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["citizen__email", "title", "description"]


from .models import CollectorPayoutSetting

@admin.register(CollectorPayoutSetting)
class CollectorPayoutSettingAdmin(admin.ModelAdmin):
    """Admin configuration for viewing and tuning collector commission formulas and payout rates."""
    list_display = ["id", "base_min_payout", "rate_per_km", "extra_weight_commission_percent", "updated_at"]


from .models import AnonymousFeedback

@admin.register(AnonymousFeedback)
class AnonymousFeedbackAdmin(admin.ModelAdmin):
    """Admin configuration for anonymous public feedback with inline review status checkbox."""
    list_display = ["id", "category", "subject", "is_reviewed", "created_at"]
    list_filter = ["category", "is_reviewed", "created_at"]
    search_fields = ["subject", "message"]
    list_editable = ["is_reviewed"]


from .models import City, Hub, Vehicle, Route, RoutePickup

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "state", "is_active", "created_at"]
    list_filter = ["is_active", "state"]
    search_fields = ["name", "state"]
    list_editable = ["is_active"]


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "city", "latitude", "longitude", "is_active", "created_at"]
    list_filter = ["is_active", "city"]
    search_fields = ["name", "city__name", "address"]
    list_editable = ["is_active"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["id", "vehicle_number", "hub", "driver", "max_capacity", "status", "created_at"]
    list_filter = ["status", "hub"]
    search_fields = ["vehicle_number", "driver__email"]


class RoutePickupInline(admin.TabularInline):
    model = RoutePickup
    extra = 0
    raw_id_fields = ["pickup_request"]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["id", "vehicle", "hub", "status", "total_distance_km", "start_time", "end_time"]
    list_filter = ["status", "hub"]
    inlines = [RoutePickupInline]


@admin.register(RoutePickup)
class RoutePickupAdmin(admin.ModelAdmin):
    list_display = ["id", "route", "pickup_request", "sequence", "status", "added_at"]
    list_filter = ["status", "route"]



