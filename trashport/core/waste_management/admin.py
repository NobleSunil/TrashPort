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
    list_display = ["id", "user", "address_line1", "city", "state", "postal_code", "is_default"]
    list_filter = ["city", "state", "is_default"]
    search_fields = ["user__email", "address_line1", "city"]

@admin.register(WasteCategory)
class WasteCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "fee_per_kg", "points_per_kg", "created_at"]
    search_fields = ["name"]

@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "citizen", "collector", "category", "weight_kg", "fee", "points_earned", "is_paid", "status", "schedule_date"]
    list_filter = ["status", "is_paid", "category"]
    search_fields = ["citizen__email", "collector__email", "id"]

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["id", "citizen", "pickup_request", "title", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["citizen__email", "title", "description"]


from .models import CollectorPayoutSetting

@admin.register(CollectorPayoutSetting)
class CollectorPayoutSettingAdmin(admin.ModelAdmin):
    list_display = ["id", "base_min_payout", "rate_per_km", "extra_weight_commission_percent", "updated_at"]


from .models import AnonymousFeedback

@admin.register(AnonymousFeedback)
class AnonymousFeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "category", "subject", "is_reviewed", "created_at"]
    list_filter = ["category", "is_reviewed", "created_at"]
    search_fields = ["subject", "message"]
    list_editable = ["is_reviewed"]


