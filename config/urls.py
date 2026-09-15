"""
config/urls.py — Master URL Configuration (Root URL Router)
============================================================

PURPOSE:
  The top-level URL configuration file. Django loads this file first when
  any request arrives. It includes all sub-apps via include() and defines
  the global URL structure.

URL STRUCTURE OVERVIEW:
  /                    → Home page (pages/home.html template)
  /about/              → About page (pages/about.html template)
  /accounts/           → django-allauth auth views (login, signup, logout, etc.)
  /api/                → REST API (config/api_router.py → /api/users/, /api/addresses/, ...)
  /api/schema/         → drf-spectacular OpenAPI schema (JSON/YAML download)
  /api/docs/           → Swagger UI for interactive API exploration
  /api/auth-token/     → DRF token authentication endpoint
  /<ADMIN_URL>/        → Django admin panel (default: /django-admin/)
  /api/maps/           → Map API (collector GPS, road routing)
  /api/collectors/     → Collector Aadhaar OTP verification API
  /                    → All other URLs handled by waste_management/urls.py
                         (dashboard, pickups, addresses, complaints, payments, etc.)

CONNECTION MAP:
  - waste_management/urls.py     → handles all citizen/collector/admin web UI URLs
  - config/api_router.py         → handles all /api/ REST endpoints
  - trashport/maps/urls.py       → handles /api/maps/ GPS and routing endpoints
  - trashport/collectors/urls.py → handles /api/collectors/aadhaar/ endpoints
  - config/settings/base.py      → ADMIN_URL, DEBUG mode for debug toolbar inclusion

ALLAUTH AUTH VIEWS (at /accounts/):
  /accounts/login/      → Sign in
  /accounts/signup/     → Register (role is set during signup)
  /accounts/logout/     → Sign out
  /accounts/password/   → Password change/reset flows

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
    path("", include("waste_management.urls")),
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
    path("api/firebase/", include("trashport.firebase.urls", namespace="api_firebase")),
    path("api/citizens/", include("trashport.citizens.urls", namespace="api_citizens")),
    path("api/collectors/", include("trashport.collectors.urls", namespace="api_collectors")),
    path("api/admins/", include("trashport.admins.urls", namespace="api_admins")),
    path("api/payments/", include("trashport.payments.urls", namespace="api_payments")),
    path("api/maps/", include("trashport.maps.urls", namespace="api_maps")),
    path("api/notifications/", include("trashport.notifications.urls", namespace="api_notifications")),
    path("api/dispatch/", include("trashport.dispatch.urls", namespace="api_dispatch")),
    path("api/chatbot/", include("trashport.chatbot.urls", namespace="api_chatbot")),
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
