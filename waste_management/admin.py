from django.contrib import admin
from .models import Address, SubscriptionTier, Subscription, WasteCategory, PickupRequest, Complaint

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "address_line1", "city", "state", "postal_code", "is_default"]
    list_filter = ["city", "state", "is_default"]
    search_fields = ["user__email", "address_line1", "city"]

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "tier", "start_date", "end_date", "is_active"]
    list_filter = ["is_active", "tier"]
    search_fields = ["user__email", "tier__name"]

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
