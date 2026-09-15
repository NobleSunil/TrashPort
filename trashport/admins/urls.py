"""
URL configuration for TrashPort Administrator & Operations portal.

Routes:
- Live tracking map of active waste collectors.
- Waste category and subscription tier management (CRUD).
- System-wide user list and verification controls.
- Automated batch pickup dispatch and assignments.
- Operations and revenue reporting with CSV export capabilities.
"""

from django.urls import path
from trashport.admins.views import AdminLiveMapView
from trashport.core.waste_management.views import (
    WasteCategoryListView,
    WasteCategoryCreateView,
    UserListView,
    AutoAssignPickupsView,
    ExportPickupsCSVView,
    ExportRevenueCSVView,
    OperationsReportView,
)

app_name = "admins"

urlpatterns = [
    # Live Real-time Collector Tracking Map
    path("live-map/", AdminLiveMapView.as_view(), name="live_map"),

    # Waste Category Configuration (Pricing, Disposal types)
    path("categories/", WasteCategoryListView.as_view(), name="category_list"),
    path("categories/new/", WasteCategoryCreateView.as_view(), name="category_create"),


    # User Management & Verification Status Reviews
    path("users/", UserListView.as_view(), name="user_list"),

    # Auto-Dispatch Algorithm Trigger (Nearest Collector / Load Balancing)
    path("auto-assign/", AutoAssignPickupsView.as_view(), name="auto_assign"),


    # Operational Analytics & Reporting
    path("reports/operations/", OperationsReportView.as_view(), name="operations_report"),

    # CSV Data Exporting Endpoints
    path("export/pickups/", ExportPickupsCSVView.as_view(), name="export_pickups"),
    path("export/revenue/", ExportRevenueCSVView.as_view(), name="export_revenue"),
]

