"""
Migration: trashport/collectors — Add CollectorAadhaarProfile

This migration adds the CollectorAadhaarProfile model which stores
Aadhaar verification state EXCLUSIVELY for Collector users.

Data protection notes:
- aadhaar_hash: SHA-256 hash only — raw Aadhaar is never stored
- aadhaar_masked: e.g. "XXXX XXXX 9012" — for display only
- otp_hash: SHA-256 hash of OTP — cleared after use
- No fields are added to the shared users.User table
"""
import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectorAadhaarProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                # OneToOne link to the Collector user (never touches other roles)
                (
                    "collector",
                    models.OneToOneField(
                        help_text="The Collector user this Aadhaar profile belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aadhaar_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Collector",
                    ),
                ),
                # Hashed + masked Aadhaar — raw number NEVER stored
                (
                    "aadhaar_hash",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "SHA-256 hex digest of the 12-digit Aadhaar number. "
                            "The raw number is never stored. Used for duplicate detection."
                        ),
                        max_length=64,
                        null=True,
                        verbose_name="Aadhaar SHA-256 Hash",
                    ),
                ),
                (
                    "aadhaar_masked",
                    models.CharField(
                        blank=True,
                        help_text='Display-safe masked string, e.g. "XXXX XXXX 9012".',
                        max_length=20,
                        null=True,
                        verbose_name="Masked Aadhaar Display",
                    ),
                ),
                (
                    "aadhaar_verified",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "True once the collector has successfully completed the "
                            "simulated Aadhaar OTP verification flow. Collector-scoped — "
                            "does not affect Admin, Citizen, or any other role."
                        ),
                        verbose_name="Aadhaar Verified",
                    ),
                ),
                # OTP session (single-use, hashed, 5-minute expiry)
                (
                    "reference_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text=(
                            "Opaque token returned to the front-end to link the initiate and "
                            "verify API calls without exposing any Aadhaar data."
                        ),
                        unique=True,
                        verbose_name="Session Reference ID",
                    ),
                ),
                (
                    "otp_hash",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "SHA-256 hash of the current pending OTP. "
                            "Cleared (set to None) after a successful verification (single-use)."
                        ),
                        max_length=64,
                        null=True,
                        verbose_name="OTP SHA-256 Hash",
                    ),
                ),
                (
                    "otp_expires_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="OTP is valid for 5 minutes from generation.",
                        null=True,
                        verbose_name="OTP Expiry",
                    ),
                ),
                (
                    "otp_attempts",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Number of verification attempts for the current OTP. Max 3.",
                        verbose_name="OTP Attempt Count",
                    ),
                ),
                # Timestamps
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Collector Aadhaar Profile",
                "verbose_name_plural": "Collector Aadhaar Profiles",
            },
        ),
    ]
