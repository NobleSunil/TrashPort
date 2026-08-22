from django.contrib import admin
from .models import PaymentTransaction, WalletHistory


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("user__email", "transaction_id", "description")


@admin.register(WalletHistory)
class WalletHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "points_delta", "balance_after", "reason", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "reason")
