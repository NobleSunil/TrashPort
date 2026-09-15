"""
URL configuration for the Collectors app.

Aadhaar verification routes (COLLECTOR-SCOPED):
  /api/collectors/aadhaar/initiate/  â€” validate Aadhaar number, generate demo OTP
  /api/collectors/aadhaar/verify/    â€” verify OTP, mark collector as aadhaar_verified

All other routes delegate to the shared waste_management views.
"""
from django.urls import path
from trashport.core.waste_management.views import DashboardView, PickupStatusUpdateView, PickupRequestDetailView

# Collector-scoped Aadhaar views (do NOT affect other roles)
from .aadhaar_views import AadhaarInitiateView, AadhaarVerifyView, AadhaarVerifyPageView

app_name = "collectors"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("jobs/<int:pk>/", PickupRequestDetailView.as_view(), name="job_detail"),
    path("jobs/<int:pk>/status/", PickupStatusUpdateView.as_view(), name="job_status"),

    # -------------------------------------------------------------------------
    # Aadhaar verification â€” Collector signup only
    # GET  /api/collectors/aadhaar/  â€” Page (HTML form)
    # POST /api/collectors/aadhaar/initiate/
    # POST /api/collectors/aadhaar/verify/
    # -------------------------------------------------------------------------
    path("aadhaar/", AadhaarVerifyPageView.as_view(), name="aadhaar_page"),
    path("aadhaar/initiate/", AadhaarInitiateView.as_view(), name="aadhaar_initiate"),
    path("aadhaar/verify/", AadhaarVerifyView.as_view(), name="aadhaar_verify"),
]
