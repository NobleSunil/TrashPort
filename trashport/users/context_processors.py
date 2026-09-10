"""
Context processors for the TrashPort users application.

Exposes global authentication settings, registration toggles, and Firebase API keys
directly to Django templates for client-side authentication bootstrapping.
"""

from django.conf import settings


def allauth_settings(request):
    """
    Expose required authentication configuration to template contexts.

    Keys:
    - ACCOUNT_ALLOW_REGISTRATION: Boolean controlling whether public signups are permitted.
    - FIREBASE_WEB_API_KEY: Public Web API Key for initializing the browser Firebase SDK.
    """
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
        "FIREBASE_WEB_API_KEY": getattr(settings, "FIREBASE_WEB_API_KEY", "YOUR_API_KEY"),
    }

