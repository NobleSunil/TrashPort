"""
REST API Router Configuration.

Registers REST framework ViewSets into automatic URL routing structures:
- /api/users/           -> User management & profile viewset
- /api/addresses/       -> Citizen pickup address book
- /api/waste-categories/-> Waste classification catalog & rates
- /api/pickup-requests/ -> Waste collection scheduling and lifecycle
- /api/complaints/      -> Citizen grievance and feedback tickets
"""

from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from trashport.users.api.views import UserViewSet
from waste_management.views import (
    AddressViewSet,
    WasteCategoryViewSet,
    PickupRequestViewSet,
    ComplaintViewSet,
)

# Use DefaultRouter in DEBUG mode to provide a browsable API root; SimpleRouter otherwise
router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# Primary REST Resource ViewSets
router.register("users", UserViewSet)
router.register("addresses", AddressViewSet, basename="address")
router.register("waste-categories", WasteCategoryViewSet, basename="wastecategory")
router.register("pickup-requests", PickupRequestViewSet, basename="pickuprequest")
router.register("complaints", ComplaintViewSet, basename="complaint")

app_name = "api"
urlpatterns = router.urls

