"""
waste_management/urls.py — Central URL Routing Hub
====================================================

PURPOSE:
  This file is the single source of truth for ALL web-facing URLs in the
  TrashPort platform. Every page a user visits — regardless of role — is
  registered here. URLs are shared across Citizen, Collector, and Admin roles;
  the role-specific view dispatchers in waste_management/views.py handle
  routing to the correct template and logic.

HOW ROLE DISPATCH WORKS WITH THESE URLS:
  A single URL like /dashboard/ is registered once here.
  When a citizen, collector, or admin visits it:
    → DashboardView (waste_management/views.py) inspects user.role
    → Delegates to CitizenDashboardView / CollectorDashboardView / AdminDashboardView

INCLUSION IN config/urls.py:
  path("", include("waste_management.urls"))     ← all URLs start from root

CONNECTION MAP:
  - config/urls.py               → includes this file (with no prefix)
  - waste_management/views.py    → provides all dispatcher + DRF ViewSet classes
  - trashport/citizens/views.py  → provides citizen-specific views (re-exported via views.py)
  - trashport/admins/views.py    → provides admin-specific views
  - trashport/collectors/views.py → provides collector-specific views

NAMING CONVENTION:
  All URL names use the "waste_management" namespace.
  Use {% url 'waste_management:dashboard' %} in templates.
  Use reverse('waste_management:dashboard') in Python views.

IMPACT:
  - Changing a URL path here changes the browser-visible URL. Update any
    hardcoded links in templates or email notifications accordingly.
  - Changing a URL name here requires updating all {% url %} tags and
    reverse() calls that use that name.
  - Adding a new URL requires: (1) add the dispatcher class in views.py,
    (2) add the URL pattern here.
"""

from django.urls import path
from trashport.admins.views import (
    AdminLiveMapView,
    CityListView, CityCreateView, CityUpdateView, CityToggleActiveView,
    HubListView, HubCreateView, HubUpdateView, HubToggleActiveView, HubDeleteView,
    VehicleListView, VehicleCreateView, VehicleUpdateView, VehicleStatusUpdateView,
    RouteListView, RouteDetailView, RouteCreateView, RouteAssignPickupView, RouteHoldPickupView,
)
from .views import (
    # === Core Navigation ===
    DashboardView,

    # === Address Management (Citizens only) ===
    AddressListView, AddressCreateView, AddressUpdateView, AddressDeleteView,

    # === Pickup Requests (Citizens create; all roles view/action) ===
    PickupRequestCreateView, PickupRequestDetailView, PickupStatusUpdateView,

    # === Complaint System (Citizens file; Admins resolve) ===
    ComplaintListView, ComplaintCreateView, ComplaintDetailView,

    # === Waste Category Management (Admins only) ===
    WasteCategoryListView, WasteCategoryCreateView, WasteCategoryUpdateView,

    # === User Administration (Admins only) ===
    UserListView, CollectorCreateView, UserDetailView,
    UserToggleActiveView, UserDeleteAdminView, CollectorVerificationView,
    WalletAdjustView, CollectorRedeemUPIView,

    # === Operations & Dispatch (Admins only) ===
    AutoAssignPickupsView, ExportPickupsCSVView, ExportRevenueCSVView,
    OperationsReportView,

    # === Payment Flow (Citizens only) ===
    PaymentCheckoutView, PaymentSuccessView, PickupInvoiceView,

    # === Payout Settings (Admins only) ===
    CollectorPayoutSettingUpdateView,

    # === Anonymous Feedback (Public — no login required) ===
    SubmitAnonymousFeedbackView,
    AdminAnonymousFeedbackListView,
)
from trashport.citizens.views import CitizenWalletView

app_name = "waste_management"

urlpatterns = [
    # ===========================================================================
    # Dashboard & Wallet
    # Role-dispatched: shows different content for Citizen / Collector / Admin
    # ===========================================================================
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Citizen's recycling green wallet — points history and coupon redemption
    path("wallet/", CitizenWalletView.as_view(), name="wallet"),
    # Collector-only: withdraw wallet cash to a UPI address
    path("wallet/redeem-upi/", CollectorRedeemUPIView.as_view(), name="collector_redeem_upi"),

    # ===========================================================================
    # Address Book (Citizens only)
    # CRUD operations for citizen pickup addresses
    # ===========================================================================
    path("addresses/", AddressListView.as_view(), name="address_list"),
    path("addresses/new/", AddressCreateView.as_view(), name="address_create"),
    path("addresses/<int:pk>/edit/", AddressUpdateView.as_view(), name="address_update"),
    path("addresses/<int:pk>/delete/", AddressDeleteView.as_view(), name="address_delete"),

    # ===========================================================================
    # Pickup Request Lifecycle
    # - Citizens create, pay, cancel, and rate pickups
    # - Collectors claim, mark transit, complete, and release pickups
    # - Admins assign, cancel, and view all pickups
    # ===========================================================================
    path("pickups/new/", PickupRequestCreateView.as_view(), name="pickup_create"),
    path("pickups/<int:pk>/", PickupRequestDetailView.as_view(), name="pickup_detail"),
    path("pickups/<int:pk>/status/", PickupStatusUpdateView.as_view(), name="pickup_status_update"),
    # Payment flow: checkout → success → invoice (all citizen-only)
    path("pickups/<int:pk>/pay/", PaymentCheckoutView.as_view(), name="payment_checkout"),
    path("pickups/<int:pk>/pay/success/", PaymentSuccessView.as_view(), name="payment_success"),
    path("pickups/<int:pk>/invoice/", PickupInvoiceView.as_view(), name="payment_invoice"),

    # ===========================================================================
    # Complaints & Anonymous Feedback
    # - Citizens file complaints against their pickup requests
    # - Any visitor can submit anonymous feedback (no login needed)
    # - Admins view and manage all complaints and feedback
    # ===========================================================================
    path("complaints/", ComplaintListView.as_view(), name="complaint_list"),
    path("complaints/new/", ComplaintCreateView.as_view(), name="complaint_create"),
    path("complaints/<int:pk>/", ComplaintDetailView.as_view(), name="complaint_detail"),
    # Public: accepts anonymous feedback via AJAX or form POST (no login required)
    path("feedback/anonymous/", SubmitAnonymousFeedbackView.as_view(), name="submit_anonymous_feedback"),
    # Admin: view and manage all anonymous feedback submissions
    path("manage/feedback/", AdminAnonymousFeedbackListView.as_view(), name="anonymous_feedback_list"),

    # ===========================================================================
    # Admin: Waste Category Management
    # Configure waste types, pricing (fee_per_kg), and recycling rewards
    # ===========================================================================
    path("manage/categories/", WasteCategoryListView.as_view(), name="category_list"),
    path("manage/categories/new/", WasteCategoryCreateView.as_view(), name="category_create"),
    path("manage/categories/<int:pk>/edit/", WasteCategoryUpdateView.as_view(), name="category_update"),

    # ===========================================================================
    # Admin: Collector Payout Formula Settings
    # Adjusts base_min_payout, rate_per_km, extra_weight_commission_percent
    # Changes here affect ALL FUTURE completed pickup earnings
    # ===========================================================================
    path("manage/payout-settings/", CollectorPayoutSettingUpdateView.as_view(), name="collector_payout_settings"),

    # ===========================================================================
    # Admin: User Administration
    # List, view, verify, suspend, and adjust wallets for all users
    # ===========================================================================
    path("manage/users/", UserListView.as_view(), name="user_list"),
    path("manage/users/collectors/new/", CollectorCreateView.as_view(), name="collector_create"),
    path("manage/users/<int:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("manage/users/<int:pk>/toggle/", UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("manage/users/<int:pk>/delete/", UserDeleteAdminView.as_view(), name="user_delete"),
    path("manage/users/<int:pk>/verify/", CollectorVerificationView.as_view(), name="collector_verify"),
    path("manage/users/<int:pk>/wallet/", WalletAdjustView.as_view(), name="user_wallet_adjust"),

    # ===========================================================================
    # Admin: Live Map, Auto-Dispatch, Reports & Exports
    # ===========================================================================
    # Real-time collector GPS tracking map
    path("manage/live-map/", AdminLiveMapView.as_view(), name="live_map"),
    # Round-robin auto-assignment of all PENDING pickups to active collectors
    path("manage/pickups/auto-assign/", AutoAssignPickupsView.as_view(), name="pickup_auto_assign"),
    # Full operations analytics report with date filtering and Chart.js graphs
    path("manage/reports/operations/", OperationsReportView.as_view(), name="operations_report"),
    # CSV download: all pickup requests (optionally filtered by date)
    path("manage/export/pickups/", ExportPickupsCSVView.as_view(), name="export_pickups_csv"),
    # CSV download: revenue summary by waste category
    path("manage/export/revenue/", ExportRevenueCSVView.as_view(), name="export_revenue_csv"),

    # ===========================================================================
    # Admin: City & Hub Infrastructure Management
    # ===========================================================================
    path("manage/cities/", CityListView.as_view(), name="city_list"),
    path("manage/cities/new/", CityCreateView.as_view(), name="city_create"),
    path("manage/cities/<int:pk>/edit/", CityUpdateView.as_view(), name="city_update"),
    path("manage/cities/<int:pk>/toggle/", CityToggleActiveView.as_view(), name="city_toggle_active"),
    path("manage/hubs/", HubListView.as_view(), name="hub_list"),
    path("manage/hubs/new/", HubCreateView.as_view(), name="hub_create"),
    path("manage/hubs/<int:pk>/edit/", HubUpdateView.as_view(), name="hub_update"),
    path("manage/hubs/<int:pk>/toggle/", HubToggleActiveView.as_view(), name="hub_toggle_active"),
    path("manage/hubs/<int:pk>/delete/", HubDeleteView.as_view(), name="hub_delete"),

    # ===========================================================================
    # Admin: Fleet & Route Operations Management
    # ===========================================================================
    path("manage/vehicles/", VehicleListView.as_view(), name="vehicle_list"),
    path("manage/vehicles/new/", VehicleCreateView.as_view(), name="vehicle_create"),
    path("manage/vehicles/<int:pk>/edit/", VehicleUpdateView.as_view(), name="vehicle_update"),
    path("manage/vehicles/<int:pk>/status/", VehicleStatusUpdateView.as_view(), name="vehicle_status_update"),
    path("manage/routes/", RouteListView.as_view(), name="route_list"),
    path("manage/routes/new/", RouteCreateView.as_view(), name="route_create"),
    path("manage/routes/<int:pk>/", RouteDetailView.as_view(), name="route_detail"),
    path("manage/routes/<int:pk>/assign/", RouteAssignPickupView.as_view(), name="route_assign_pickup"),
    path("manage/routes/pickups/<int:pk>/hold/", RouteHoldPickupView.as_view(), name="route_hold_pickup"),
]
