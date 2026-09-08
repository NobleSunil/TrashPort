"""
Django admin registration for the Collectors app.

CollectorAadhaarProfile is registered here so administrators can:
  - See which collectors have completed Aadhaar verification
  - View masked Aadhaar display strings (never the raw number)
  - Manually reset or revoke verification if needed

Privacy safeguards:
  - aadhaar_hash is read-only in admin (cannot be edited)
  - The raw Aadhaar number is never stored and therefore never shown
"""
from django.contrib import admin
from .models import CollectorAadhaarProfile


@admin.register(CollectorAadhaarProfile)
class CollectorAadhaarProfileAdmin(admin.ModelAdmin):
    """
    Admin view for Aadhaar verification profiles.

    Only shows masked Aadhaar data — the raw number is never stored
    anywhere and therefore cannot be displayed.
    """

    list_display = [
        "collector",
        "aadhaar_verified",
        "aadhaar_masked",
        "linked_email",
        "otp_attempts",
        "otp_expires_at",
        "updated_at",
    ]
    list_filter = ["aadhaar_verified"]
    search_fields = ["collector__email", "collector__name", "aadhaar_masked"]
    ordering = ["-updated_at"]

    # aadhaar_hash is stored as a hash — show it read-only for audit,
    # but never allow editing (it's meaningless without the original number)
    readonly_fields = [
        "aadhaar_hash",
        "reference_id",
        "otp_hash",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Collector", {
            "fields": ("collector",),
        }),
        ("Aadhaar Status (DEMO MODE — Simulated)", {
            "description": (
                "⚠ DEMO/ACADEMIC PROJECT: This is a simulated Aadhaar verification. "
                "No real UIDAI data is stored. Only hashed and masked values appear here."
            ),
            "fields": ("aadhaar_verified", "aadhaar_masked", "aadhaar_hash", "linked_email"),
        }),
        ("OTP Session (read-only)", {
            "classes": ("collapse",),
            "fields": ("reference_id", "otp_hash", "otp_expires_at", "otp_attempts"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )
