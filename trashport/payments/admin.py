from django.contrib import admin
from .models import PaymentTransaction, WalletHistory, UPIPayoutRequest


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "payment_method", "status", "transaction_id", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("user__email", "transaction_id", "description")
    readonly_fields = ("transaction_id", "created_at", "updated_at")


@admin.register(WalletHistory)
class WalletHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "points_delta", "balance_after", "reason", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "reason")
    readonly_fields = ("created_at",)


@admin.register(UPIPayoutRequest)
class UPIPayoutRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "collector", "amount", "upi_id", "transaction_ref", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("collector__email", "upi_id", "transaction_ref")
    readonly_fields = ("created_at", "updated_at")
