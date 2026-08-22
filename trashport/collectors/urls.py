from django.urls import path
from waste_management.views import DashboardView, PickupStatusUpdateView, PickupRequestDetailView

app_name = "collectors"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("jobs/<int:pk>/", PickupRequestDetailView.as_view(), name="job_detail"),
    path("jobs/<int:pk>/status/", PickupStatusUpdateView.as_view(), name="job_status"),
]
