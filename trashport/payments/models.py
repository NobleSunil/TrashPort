from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class PaymentTransaction(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        REFUNDED = "REFUNDED", _("Refunded")

    class PaymentMethods(models.TextChoices):
        STRIPE = "STRIPE", _("Stripe")
        WALLET = "WALLET", _("Wallet Points")
        COD = "COD", _("Cash On Delivery")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethods.choices,
        default=PaymentMethods.STRIPE,
    )
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.PENDING,
    )
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - ${self.amount} ({self.status})"


class WalletHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet_records",
    )
    points_delta = models.IntegerField(help_text="Positive for additions, negative for deductions")
    balance_after = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.points_delta:+d} pts ({self.reason})"


class UPIPayoutRequest(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upi_payouts",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    upi_id = models.CharField(max_length=100, help_text=_("UPI VPA (e.g. user@okaxis or 9876543210@paytm)"))
    transaction_ref = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.COMPLETED,
    )
    note = models.CharField(max_length=255, blank=True, default="Redeemed to UPI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"UPI Payout: Rs. {self.amount} to {self.upi_id} ({self.status})"
