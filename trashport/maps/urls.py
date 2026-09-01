from django.urls import path
from .views import (
    ServiceZoneListView,
    CollectorLocationListView,
    update_collector_location_view,
    live_map_data_view,
    pickup_live_tracking_view,
)

app_name = "maps"

urlpatterns = [
    path("zones/", ServiceZoneListView.as_view(), name="zones"),
    path("locations/", CollectorLocationListView.as_view(), name="collector_locations"),
    path("locations/update/", update_collector_location_view, name="update_location"),
    path("live-overview/", live_map_data_view, name="live_overview"),
    path("tracking/<int:pickup_id>/", pickup_live_tracking_view, name="pickup_tracking"),
]
