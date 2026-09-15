"""
config/urls.py Ã¢â‚¬â€ Master URL Configuration (Root URL Router)
============================================================

PURPOSE:
  The top-level URL configuration file. Django loads this file first when
  any request arrives. It includes all sub-apps via include() and defines
  the global URL structure.

URL STRUCTURE OVERVIEW:
  /                    Ã¢â€ â€™ Home page (pages/home.html template)
  /about/              Ã¢â€ â€™ About page (pages/about.html template)
  /accounts/           Ã¢â€ â€™ django-allauth auth views (login, signup, logout, etc.)
  /api/                Ã¢â€ â€™ REST API (config/api_router.py Ã¢â€ â€™ /api/users/, /api/addresses/, ...)
  /api/schema/         Ã¢â€ â€™ drf-spectacular OpenAPI schema (JSON/YAML download)
  /api/docs/           Ã¢â€ â€™ Swagger UI for interactive API exploration
  /api/auth-token/     Ã¢â€ â€™ DRF token authentication endpoint
  /<ADMIN_URL>/        Ã¢â€ â€™ Django admin panel (default: /django-admin/)
  /api/maps/           Ã¢â€ â€™ Map API (collector GPS, road routing)
  /api/collectors/     Ã¢â€ â€™ Collector Aadhaar OTP verification API
  /                    Ã¢â€ â€™ All other URLs handled by waste_management/urls.py
                         (dashboard, pickups, addresses, complaints, payments, etc.)

CONNECTION MAP:
  - waste_management/urls.py     Ã¢â€ â€™ handles all citizen/collector/admin web UI URLs
  - config/api_router.py         Ã¢â€ â€™ handles all /api/ REST endpoints
  - trashport/maps/urls.py       Ã¢â€ â€™ handles /api/maps/ GPS and routing endpoints
  - trashport/collectors/urls.py Ã¢â€ â€™ handles /api/collectors/aadhaar/ endpoints
  - config/settings/base.py      Ã¢â€ â€™ ADMIN_URL, DEBUG mode for debug toolbar inclusion

ALLAUTH AUTH VIEWS (at /accounts/):
  /accounts/login/      Ã¢â€ â€™ Sign in
  /accounts/signup/     Ã¢â€ â€™ Register (role is set during signup)
  /accounts/logout/     Ã¢â€ â€™ Sign out
  /accounts/password/   Ã¢â€ â€™ Password change/reset flows

IMPACT:
  - Changing a URL prefix here changes ALL sub-URLs under it.
  - The waste_management include has NO prefix (path("", include(...))), meaning
    ALL waste_management URLs are at the root domain level.
  - DEBUG toolbar is only mounted when settings.DEBUG = True (local dev only).
  - Adding a new sub-app: create its urls.py, then add an include() line here.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("trashport.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("", include("trashport.core.waste_management.urls")),
    # Citizen-facing pages (wallet, etc.)
    path("citizen/", include("trashport.citizens.urls", namespace="citizens")),
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    path("api/firebase/", include("trashport.services.firebase.urls", namespace="api_firebase")),
    path("api/citizens/", include("trashport.citizens.urls", namespace="api_citizens")),
    path("api/collectors/", include("trashport.collectors.urls", namespace="api_collectors")),
    path("api/admins/", include("trashport.admins.urls", namespace="api_admins")),
    path("api/payments/", include("trashport.services.payments.urls", namespace="api_payments")),
    path("api/maps/", include("trashport.core.maps.urls", namespace="api_maps")),
    path("api/notifications/", include("trashport.services.notifications.urls", namespace="api_notifications")),
    path("api/dispatch/", include("trashport.services.dispatch.urls", namespace="api_dispatch")),
    path("api/chatbot/", include("trashport.services.chatbot.urls", namespace="api_chatbot")),
    # DRF auth token
    path("api/auth-token/", obtain_auth_token, name="obtain_auth_token"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
