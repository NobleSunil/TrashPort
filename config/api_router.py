"""
config/api_router.py — REST API Router Configuration
======================================================

PURPOSE:
  Registers all Django REST Framework ViewSets into automatic URL routes.
  This is the central registry for all JSON API endpoints at /api/....

ROUTED ENDPOINTS:
  /api/users/           â†’ UserViewSet          (trashport/users/api/views.py)
  /api/addresses/       â†’ AddressViewSet       (waste_management/views.py)
  /api/waste-categories/â†’ WasteCategoryViewSet (waste_management/views.py)
  /api/pickup-requests/ â†’ PickupRequestViewSet (waste_management/views.py)
  /api/complaints/      â†’ ComplaintViewSet     (waste_management/views.py)

INCLUDED IN:
  config/urls.py â†’ path("api/", include("config.api_router"))

ROUTER TYPE:
  - DEBUG=True  â†’ DefaultRouter  (includes browsable /api/ root listing)
  - DEBUG=False â†’ SimpleRouter   (no browsable root, faster, no extra URL)

CONNECTION MAP:
  - config/urls.py        â†’ includes this file at /api/ prefix
  - waste_management/views.py â†’ provides the ViewSet classes
  - trashport/users/api/views.py â†’ provides UserViewSet

IMPACT:
  - Adding a new ViewSet: import it here and call router.register().
  - Changing a basename affects the auto-generated URL names
    (e.g., "address-list", "address-detail", "address-create", etc.).
  - All endpoints are currently public (AllowAny). To restrict access,
    add permission_classes to each ViewSet class.
"""

from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from trashport.users.api.views import UserViewSet
from trashport.core.waste_management.views import (
    AddressViewSet,
    WasteCategoryViewSet,
    PickupRequestViewSet,
    ComplaintViewSet,
    CityViewSet,
    HubViewSet,
    VehicleViewSet,
    RouteViewSet,
)

# Use DefaultRouter in DEBUG mode to provide a browsable API root; SimpleRouter otherwise
router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# Primary REST Resource ViewSets
router.register("users", UserViewSet)
router.register("addresses", AddressViewSet, basename="address")
router.register("waste-categories", WasteCategoryViewSet, basename="wastecategory")
router.register("pickup-requests", PickupRequestViewSet, basename="pickuprequest")
router.register("complaints", ComplaintViewSet, basename="complaint")
router.register("cities", CityViewSet, basename="city")
router.register("hubs", HubViewSet, basename="hub")
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("routes", RouteViewSet, basename="route")

app_name = "api"
urlpatterns = router.urls

