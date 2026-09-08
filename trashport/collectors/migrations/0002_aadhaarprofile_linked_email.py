"""
Migration: Add linked_email field to CollectorAadhaarProfile

Adds the email address the collector claims is linked to their Aadhaar.
In demo mode, the OTP is "sent" to this address (logged/displayed on screen).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("collectors", "0001_aadhaar_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectoraadhaarprofile",
            name="linked_email",
            field=models.EmailField(
                blank=True,
                help_text=(
                    "Email address the collector claims is linked to their Aadhaar. "
                    "In demo mode, the OTP is 'sent' to this address (logged to console). "
                    "Voluntarily provided — not verified against UIDAI."
                ),
                max_length=254,
                null=True,
                verbose_name="Aadhaar-Linked Email",
            ),
        ),
    ]
