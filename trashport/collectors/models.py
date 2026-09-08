"""
Collector domain models — Aadhaar Verification Profile.

SCOPE: This module contains the CollectorAadhaarProfile model, which stores
Aadhaar verification state EXCLUSIVELY for Collector users. It is intentionally
kept separate from the shared users.User table so that adding/modifying this
model has absolutely zero effect on Admin, Citizen, or any other role.

DEMO / ACADEMIC PROJECT NOTE:
  AADHAAR_MODE = demo
  This implementation is a simulated flow for a college/university project.
  It does NOT connect to UIDAI or any live government authentication service.
  Doing so without an AUA/KUA license (Aadhaar Act 2016, Section 4) is illegal.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class CollectorAadhaarProfile(models.Model):
    """
    Stores Aadhaar verification state for a single Collector user.

    Privacy-by-design:
    - Raw Aadhaar number is NEVER stored.
    - Only a SHA-256 hash (aadhaar_hash) and a masked display string
      (e.g., "XXXX XXXX 9012") are persisted.
    - OTP is also stored only as a SHA-256 hash; cleared after use.

    Scoping note:
    - This model is linked to users.User via OneToOneField.
    - Only Collector accounts should ever have an instance of this model.
    - No changes to users.User are made; aadhaar_verified is COLLECTOR-ONLY.
    """

    # -------------------------------------------------------------------------
    # Relationship — Collector only
    # -------------------------------------------------------------------------
    collector = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aadhaar_profile",
        help_text="The Collector user this Aadhaar profile belongs to.",
    )

    # -------------------------------------------------------------------------
    # Aadhaar identity data — hashed & masked only, never plaintext
    # -------------------------------------------------------------------------
    aadhaar_hash = models.CharField(
        "Aadhaar SHA-256 Hash",
        max_length=64,
        blank=True,
        null=True,
        help_text=(
            "SHA-256 hex digest of the 12-digit Aadhaar number. "
            "The raw number is never stored. Used for duplicate detection."
        ),
    )
    aadhaar_masked = models.CharField(
        "Masked Aadhaar Display",
        max_length=20,
        blank=True,
        null=True,
        help_text='Display-safe masked string, e.g. "XXXX XXXX 9012".',
    )
    aadhaar_verified = models.BooleanField(
        "Aadhaar Verified",
        default=False,
        help_text=(
            "True once the collector has successfully completed the simulated "
            "Aadhaar OTP verification flow. Collector-scoped — does not affect "
            "Admin, Citizen, or any other role."
        ),
    )

    # -------------------------------------------------------------------------
    # OTP session state (single-use, 5-minute expiry)
    # -------------------------------------------------------------------------
    reference_id = models.UUIDField(
        "Session Reference ID",
        default=uuid.uuid4,
        unique=True,
        help_text=(
            "Opaque token returned to the front-end to link the initiate and "
            "verify API calls without exposing any Aadhaar data."
        ),
    )
    otp_hash = models.CharField(
        "OTP SHA-256 Hash",
        max_length=64,
        blank=True,
        null=True,
        help_text=(
            "SHA-256 hash of the current pending OTP. "
            "Cleared (set to None) after a successful verification (single-use)."
        ),
    )
    otp_expires_at = models.DateTimeField(
        "OTP Expiry",
        null=True,
        blank=True,
        help_text="OTP is valid for 5 minutes from generation.",
    )
    otp_attempts = models.PositiveSmallIntegerField(
        "OTP Attempt Count",
        default=0,
        help_text="Number of verification attempts for the current OTP. Max 3.",
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Collector Aadhaar Profile"
        verbose_name_plural = "Collector Aadhaar Profiles"

    def __str__(self):
        status = "✓ Verified" if self.aadhaar_verified else "⏳ Pending"
        return f"AadhaarProfile({self.collector.email}) — {status}"

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def is_otp_expired(self) -> bool:
        """Return True if the OTP has passed its 5-minute window."""
        if not self.otp_expires_at:
            return True
        return timezone.now() > self.otp_expires_at

    def is_otp_locked(self) -> bool:
        """Return True if the collector has exhausted all OTP attempts (max 3)."""
        return self.otp_attempts >= 3

    def reset_otp(self):
        """Clear OTP fields after successful verification (makes it single-use)."""
        self.otp_hash = None
        self.otp_expires_at = None
        self.otp_attempts = 0
        self.save(update_fields=["otp_hash", "otp_expires_at", "otp_attempts", "updated_at"])
