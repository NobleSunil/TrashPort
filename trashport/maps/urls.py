from django.urls import path
from .views import (
    ServiceZoneListView,
    CollectorLocationListView,
    update_collector_location_view,
)

app_name = "maps"

urlpatterns = [
    path("zones/", ServiceZoneListView.as_view(), name="zones"),
    path("locations/", CollectorLocationListView.as_view(), name="collector_locations"),
    path("locations/update/", update_collector_location_view, name="update_location"),
]
