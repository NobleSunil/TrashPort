# Generated manually for FAQ, ChatFeedback, ChatLog models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FAQ",
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
                ("question", models.CharField(max_length=500)),
                ("answer", models.TextField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("pickup", "Pickup"),
                            ("payment", "Payment"),
                            ("account", "Account"),
                            ("general", "General"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "FAQ",
                "verbose_name_plural": "FAQs",
                "ordering": ["category", "question"],
            },
        ),
        migrations.CreateModel(
            name="ChatFeedback",
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
                ("user_message", models.TextField()),
                ("bot_message", models.TextField()),
                (
                    "rating",
                    models.CharField(
                        choices=[
                            ("thumbs_up", "👍 Thumbs Up"),
                            ("thumbs_down", "👎 Thumbs Down"),
                        ],
                        max_length=20,
                    ),
                ),
                ("session_key", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Chat Feedback",
                "verbose_name_plural": "Chat Feedback",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatLog",
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
                ("user_message", models.TextField()),
                ("raw_llm_output", models.TextField()),
                ("parsed_output", models.JSONField(default=dict)),
                ("was_valid", models.BooleanField(default=True)),
                ("action_taken", models.CharField(blank=True, max_length=100)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Chat Log",
                "verbose_name_plural": "Chat Logs",
                "ordering": ["-created_at"],
            },
        ),
    ]
