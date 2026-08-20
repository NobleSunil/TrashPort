from django.conf import settings


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
        "FIREBASE_WEB_API_KEY": getattr(settings, "FIREBASE_WEB_API_KEY", "YOUR_API_KEY"),
    }
