"""
Waste Management View Layer — Role-Based Dispatcher & REST API Viewsets.
==========================================================================

PURPOSE:
  This file serves TWO distinct purposes:

  1. REST API Viewsets (DRF):
     - AddressViewSet, WasteCategoryViewSet, PickupRequestViewSet, ComplaintViewSet
     - These are registered in config/api_router.py and serve JSON responses
       at /api/addresses/, /api/waste-categories/, etc.

  2. Role-Based Web UI Dispatchers:
     - DashboardView, PickupRequestDetailView, PickupStatusUpdateView, etc.
     - These are the URL endpoints used in waste_management/urls.py
     - They inspect the logged-in user's role (CITIZEN / COLLECTOR / ADMIN)
       and delegate the request to the appropriate role-specific view class
       located in trashport/citizens/views.py, trashport/collectors/views.py,
       or trashport/admins/views.py.

CONNECTION MAP:
  - config/urls.py            → includes waste_management/urls.py
  - waste_management/urls.py  → references the dispatcher classes defined here
  - Each dispatcher           → imports and delegates to role-specific views:
      • trashport/citizens/views.py   (CitizenDashboardView, etc.)
      • trashport/collectors/views.py (CollectorDashboardView, etc.)
      • trashport/admins/views.py     (AdminDashboardView, etc.)
  - config/api_router.py      → registers the DRF ViewSets defined here

IMPACT:
  - If you add a new role, add it to the dispatcher's role_map dictionary.
  - If you add a new role-specific view, create a new dispatcher class here
    and register it in waste_management/urls.py.
  - Modifying the DRF ViewSets affects the JSON API responses only.
"""

import importlib

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.views.generic import View
from rest_framework import permissions as drf_permissions
from rest_framework import viewsets

# ---------------------------------------------------------------------------
# Re-export role-specific view imports so urls.py pattern resolution works.
# These imports are consumed by waste_management/urls.py when it does:
#   from .views import WasteCategoryListView, WasteCategoryCreateView, ...
#
# CONNECTION: waste_management/urls.py depends on these re-exports.
# IMPACT: Removing any of these imports will break the corresponding URL route.
# ---------------------------------------------------------------------------
from trashport.admins.views import (
    WasteCategoryCreateView,
    WasteCategoryListView,
    WasteCategoryUpdateView,
    CollectorPayoutSettingUpdateView,
    AdminAnonymousFeedbackListView,
)
from trashport.citizens.views import (
    AddressCreateView,
    AddressDeleteView,
    AddressListView,
    AddressUpdateView,
    SubmitAnonymousFeedbackView,
    CitizenComplaintCreateView as ComplaintCreateView,
    CitizenPickupRequestCreateView as PickupRequestCreateView,
)

from .models import Address, WasteCategory, PickupRequest, Complaint
from .serializers import (
    AddressSerializer,
    WasteCategorySerializer,
    PickupRequestSerializer,
    ComplaintSerializer,
)

User = get_user_model()


# ==============================================================================
# REST API Viewsets (for Django Rest Framework)
# ==============================================================================
#
# These viewsets provide standard CRUD JSON API endpoints.
# They are registered in config/api_router.py and accessible at:
#   - /api/addresses/
#   - /api/waste-categories/
#   - /api/pickup-requests/
#   - /api/complaints/
#
# CONNECTION: config/api_router.py registers these viewsets.
# IMPACT: Changing queryset or serializer_class affects all API consumers.
# ==============================================================================

class AddressViewSet(viewsets.ModelViewSet):
    """REST API for citizen pickup addresses."""
    queryset = Address.objects.all().order_by("-created_at")
    serializer_class = AddressSerializer
    permission_classes = [drf_permissions.AllowAny]


class WasteCategoryViewSet(viewsets.ModelViewSet):
    """REST API for waste classification categories and pricing."""
    queryset = WasteCategory.objects.all().order_by("name")
    serializer_class = WasteCategorySerializer
    permission_classes = [drf_permissions.AllowAny]


class PickupRequestViewSet(viewsets.ModelViewSet):
    """REST API for waste collection pickup requests."""
    queryset = PickupRequest.objects.all().order_by("-schedule_date")
    serializer_class = PickupRequestSerializer
    permission_classes = [drf_permissions.AllowAny]


class ComplaintViewSet(viewsets.ModelViewSet):
    """REST API for citizen complaint/grievance tickets."""
    queryset = Complaint.objects.all().order_by("-created_at")
    serializer_class = ComplaintSerializer
    permission_classes = [drf_permissions.AllowAny]


# ==============================================================================
# Role-Based Dispatch System
# ==============================================================================
#
# HOW IT WORKS:
#   Every web UI URL in waste_management/urls.py points to a "dispatcher" class.
#   When a request arrives, the dispatcher checks the user's role and forwards
#   the request to the correct role-specific view class.
#
#   Example flow:
#     1. User visits /dashboard/
#     2. waste_management/urls.py routes to DashboardView (defined below)
#     3. DashboardView checks user.role:
#        - CITIZEN  → delegates to CitizenDashboardView  (citizens/views.py)
#        - COLLECTOR → delegates to CollectorDashboardView (collectors/views.py)
#        - ADMIN    → delegates to AdminDashboardView     (admins/views.py)
#     4. The role-specific view handles the request and returns the response.
#
# WHY THIS PATTERN:
#   - Single URL endpoint per feature (e.g., /dashboard/) instead of
#     /citizen/dashboard/, /collector/dashboard/, /admin/dashboard/
#   - Role-based access control is centralized here
#   - Templates can use {% url 'waste_management:dashboard' %} universally
#
# ADDING A NEW DISPATCHER:
#   1. Create a new class inheriting from RoleDispatchView
#   2. Set role_map = { role: "dotted.path.to.ViewClass", ... }
#   3. Register it in waste_management/urls.py
#
# IMPACT:
#   - Modifying role_map changes which view class handles each role.
#   - Adding 'dispatch_methods' controls which HTTP methods are forwarded.
#   - Superusers are always treated as ADMIN role.
# ==============================================================================


class RoleDispatchView(LoginRequiredMixin, View):
    """
    Base dispatcher that routes requests to role-specific view classes.

    Subclasses define a `role_map` dictionary mapping User.Roles values to
    the dotted import path of the target view class. The dispatcher dynamically
    imports and instantiates the correct view at request time.

    Attributes:
        role_map (dict): Maps role constants to "module.path.ClassName" strings.
                         Example: { User.Roles.CITIZEN: "trashport.citizens.views.CitizenDashboardView" }

    Security:
        - Requires login (LoginRequiredMixin)
        - Returns HTTP 403 Forbidden for unmapped roles
        - Superusers are automatically treated as ADMIN
    """

    # -------------------------------------------------------------------------
    # Subclasses MUST override this mapping.
    # Keys   = User.Roles enum values (e.g., User.Roles.CITIZEN)
    # Values = Dotted import path to the role-specific view class
    # -------------------------------------------------------------------------
    role_map = {}

    def dispatch(self, request, *args, **kwargs):
        """
        Intercepts all HTTP methods (GET, POST, etc.) and forwards to the
        appropriate role-specific view class based on the logged-in user's role.

        FLOW:
          1. Determine user's role (superusers → ADMIN)
          2. Look up the target view class in role_map
          3. Dynamically import the view class
          4. Instantiate and call its as_view() to handle the request
          5. Return HTTP 403 if no mapping exists for the role
        """
        # ---- Step 1: Determine effective role ----
        role = getattr(request.user, "role", None)
        if request.user.is_superuser:
            role = User.Roles.ADMIN

        # ---- Step 2: Look up target view path ----
        view_path = self.role_map.get(role)
        if not view_path:
            return HttpResponseForbidden("Invalid role")

        # ---- Step 3: Dynamically import the view class ----
        # Split "trashport.citizens.views.CitizenDashboardView" into
        # module = "trashport.citizens.views" and class_name = "CitizenDashboardView"
        module_path, class_name = view_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        view_class = getattr(module, class_name)

        # ---- Step 4: Delegate to the role-specific view ----
        return view_class.as_view()(request, *args, **kwargs)


# ==============================================================================
# Dispatcher Instances — One per feature / URL endpoint
# ==============================================================================
#
# Each class below maps a single URL endpoint to up to 3 role-specific views.
# The naming convention is: <Feature>View → dispatches to
#   Citizen<Feature>View, Collector<Feature>View, Admin<Feature>View
#
# CONNECTION: Each class is referenced by name in waste_management/urls.py
# ==============================================================================


class DashboardView(RoleDispatchView):
    """
    URL: /dashboard/
    Routes to the role-appropriate dashboard:
      - CITIZEN  → CitizenDashboardView  (trashport/citizens/views.py)
      - COLLECTOR → CollectorDashboardView (trashport/collectors/views.py)
      - ADMIN    → AdminDashboardView     (trashport/admins/views.py)
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenDashboardView",
        User.Roles.COLLECTOR: "trashport.collectors.views.CollectorDashboardView",
        User.Roles.ADMIN: "trashport.admins.views.AdminDashboardView",
    }


class PickupRequestDetailView(RoleDispatchView):
    """
    URL: /pickups/<int:pk>/
    Routes pickup detail display to the role's specific view.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenPickupRequestDetailView",
        User.Roles.COLLECTOR: "trashport.collectors.views.CollectorPickupRequestDetailView",
        User.Roles.ADMIN: "trashport.admins.views.AdminPickupRequestDetailView",
    }


class PickupStatusUpdateView(RoleDispatchView):
    """
    URL: /pickups/<int:pk>/status/  (POST only)
    Routes pickup status changes (claim, transit, complete, cancel, feedback)
    to the role's specific handler.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenPickupStatusUpdateView",
        User.Roles.COLLECTOR: "trashport.collectors.views.CollectorPickupStatusUpdateView",
        User.Roles.ADMIN: "trashport.admins.views.AdminPickupStatusUpdateView",
    }


class ComplaintListView(RoleDispatchView):
    """
    URL: /complaints/
    Routes complaint list to either Citizen's or Admin's view.
    Collectors do not have a complaints view.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenComplaintListView",
        User.Roles.ADMIN: "trashport.admins.views.AdminComplaintListView",
    }


class ComplaintDetailView(RoleDispatchView):
    """
    URL: /complaints/<int:pk>/
    Routes complaint detail (GET) and resolution (POST) to Citizen or Admin view.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenComplaintDetailView",
        User.Roles.ADMIN: "trashport.admins.views.AdminComplaintDetailView",
    }


class UserListView(RoleDispatchView):
    """
    URL: /manage/users/
    Admin-only: lists all users with role filtering and verification controls.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminUserListView",
    }


class CollectorCreateView(RoleDispatchView):
    """
    URL: /manage/users/collectors/new/
    Admin-only: provisions new verified collector accounts.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminCollectorCreateView",
    }


class UserDetailView(RoleDispatchView):
    """
    URL: /manage/users/<int:pk>/
    Admin-only: shows full user profile with addresses, wallet, pickup history.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminUserDetailView",
    }


class UserToggleActiveView(RoleDispatchView):
    """
    URL: /manage/users/<int:pk>/toggle/  (POST only)
    Admin-only: suspends or reactivates a user account.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminUserToggleActiveView",
    }


class CollectorVerificationView(RoleDispatchView):
    """
    URL: /manage/users/<int:pk>/verify/  (POST only)
    Admin-only: approves or rejects a collector's verification status.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminCollectorVerificationView",
    }


class CollectorRedeemUPIView(RoleDispatchView):
    """
    URL: /wallet/redeem-upi/  (POST only)
    Collector-only: redeems wallet cash balance to UPI.
    """
    role_map = {
        User.Roles.COLLECTOR: "trashport.collectors.views.CollectorRedeemUPIView",
    }


class WalletAdjustView(RoleDispatchView):
    """
    URL: /manage/users/<int:pk>/wallet/  (POST only)
    Admin-only: credits or debits wallet points for a user.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminWalletAdjustView",
    }


class AutoAssignPickupsView(RoleDispatchView):
    """
    URL: /manage/pickups/auto-assign/  (POST only)
    Admin-only: auto-assigns all pending pickups to available collectors.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminAutoAssignPickupsView",
    }


class ExportPickupsCSVView(RoleDispatchView):
    """
    URL: /manage/export/pickups/
    Admin-only: generates CSV export of all pickup requests.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminExportPickupsCSVView",
    }


class ExportRevenueCSVView(RoleDispatchView):
    """
    URL: /manage/export/revenue/
    Admin-only: generates CSV financial report by waste category.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminExportRevenueCSVView",
    }


class OperationsReportView(RoleDispatchView):
    """
    URL: /manage/reports/operations/
    Admin-only: renders operations analytics and KPI report.
    """
    role_map = {
        User.Roles.ADMIN: "trashport.admins.views.AdminOperationsReportView",
    }


class PaymentCheckoutView(RoleDispatchView):
    """
    URL: /pickups/<int:pk>/pay/
    Citizen-only: renders the payment checkout page for a pickup request.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenPaymentCheckoutView",
    }


class PaymentSuccessView(RoleDispatchView):
    """
    URL: /pickups/<int:pk>/pay/success/
    Citizen-only: displays payment success receipt.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenPaymentSuccessView",
    }


class PickupInvoiceView(RoleDispatchView):
    """
    URL: /pickups/<int:pk>/invoice/
    Citizen and Admin: renders official tax invoice / payment receipt.
    Both citizens (for their own pickups) and admins can view invoices.
    """
    role_map = {
        User.Roles.CITIZEN: "trashport.citizens.views.CitizenInvoiceView",
        User.Roles.ADMIN: "trashport.citizens.views.CitizenInvoiceView",
    }
