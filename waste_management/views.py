"""
Waste Management View Layer.
Provides shared REST API Viewsets for Django Rest Framework (DRF)
and serves as the Dispatch/Routing layer for role-specific Web UI Views (Citizen, Collector, Admin).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.views.generic import View
from rest_framework import permissions as drf_permissions
from rest_framework import viewsets

# Expose role-specific view imports so urls.py pattern resolution works transparently
from trashport.admins.views import (
    WasteCategoryCreateView,
    WasteCategoryListView,
    WasteCategoryUpdateView,
)
from trashport.citizens.views import (
    AddressCreateView,
    AddressDeleteView,
    AddressListView,
    AddressUpdateView,
    CitizenComplaintCreateView as ComplaintCreateView,
    CitizenPickupRequestCreateView as PickupRequestCreateView,
)
from .models import Address, Complaint, PickupRequest, WasteCategory
from .serializers import (
    AddressSerializer,
    ComplaintSerializer,
    PickupRequestSerializer,
    WasteCategorySerializer,
)

User = get_user_model()

# ==============================================================================
# REST API Viewsets (for DRF)
# ==============================================================================

class AddressViewSet(viewsets.ModelViewSet):
    """
    API viewset for Address instances.
    """
    queryset = Address.objects.all().order_by("-created_at")
    serializer_class = AddressSerializer
    permission_classes = [drf_permissions.AllowAny]


class WasteCategoryViewSet(viewsets.ModelViewSet):
    """
    API viewset for WasteCategory instances.
    """
    queryset = WasteCategory.objects.all().order_by("name")
    serializer_class = WasteCategorySerializer
    permission_classes = [drf_permissions.AllowAny]


class PickupRequestViewSet(viewsets.ModelViewSet):
    """
    API viewset for PickupRequest instances.
    """
    queryset = PickupRequest.objects.all().order_by("-schedule_date")
    serializer_class = PickupRequestSerializer
    permission_classes = [drf_permissions.AllowAny]


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    API viewset for Complaint instances.
    """
    queryset = Complaint.objects.all().order_by("-created_at")
    serializer_class = ComplaintSerializer
    permission_classes = [drf_permissions.AllowAny]


# ==============================================================================
# Dispatch / Routing Layer for Web UI Views
# ==============================================================================

class DashboardView(LoginRequiredMixin, View):
    """
    Routes the logged-in user to their respective Dashboard view based on their role
    (Citizen, Collector, or Admin).
    """
    def get(self, request, *args, **kwargs):
        if request.user.role == User.Roles.CITIZEN:
            from trashport.citizens.views import CitizenDashboardView
            return CitizenDashboardView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.COLLECTOR:
            from trashport.collectors.views import CollectorDashboardView
            return CollectorDashboardView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.ADMIN:
            from trashport.admins.views import AdminDashboardView
            return AdminDashboardView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Invalid role")


class PickupRequestDetailView(LoginRequiredMixin, View):
    """
    Routes the pickup request detail display to the respective role's view logic
    (Citizen, Collector, or Admin).
    """
    def get(self, request, *args, **kwargs):
        if request.user.role == User.Roles.CITIZEN:
            from trashport.citizens.views import CitizenPickupRequestDetailView
            return CitizenPickupRequestDetailView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.COLLECTOR:
            from trashport.collectors.views import CollectorPickupRequestDetailView
            return CollectorPickupRequestDetailView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.ADMIN:
            from trashport.admins.views import AdminPickupRequestDetailView
            return AdminPickupRequestDetailView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Invalid role")


class PickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Dispatches pickup status updates to the respective role's POST action logic.
    """
    def post(self, request, *args, **kwargs):
        if request.user.role == User.Roles.CITIZEN:
            from trashport.citizens.views import CitizenPickupStatusUpdateView
            return CitizenPickupStatusUpdateView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.COLLECTOR:
            from trashport.collectors.views import CollectorPickupStatusUpdateView
            return CollectorPickupStatusUpdateView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.ADMIN:
            from trashport.admins.views import AdminPickupStatusUpdateView
            return AdminPickupStatusUpdateView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Invalid role")


class ComplaintListView(LoginRequiredMixin, View):
    """
    Dispatches complaint listings to either the Citizen's or Admin's view classes.
    """
    def get(self, request, *args, **kwargs):
        if request.user.role == User.Roles.CITIZEN:
            from trashport.citizens.views import CitizenComplaintListView
            return CitizenComplaintListView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.ADMIN:
            from trashport.admins.views import AdminComplaintListView
            return AdminComplaintListView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Invalid role")


class ComplaintDetailView(LoginRequiredMixin, View):
    """
    Dispatches complaint detail views (GET) and resolutions (POST) to either the Citizen
    or Admin view classes.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.role == User.Roles.CITIZEN:
            from trashport.citizens.views import CitizenComplaintDetailView
            return CitizenComplaintDetailView.as_view()(request, *args, **kwargs)
        elif request.user.role == User.Roles.ADMIN:
            from trashport.admins.views import AdminComplaintDetailView
            return AdminComplaintDetailView.as_view()(request, *args, **kwargs)
        return HttpResponseForbidden("Invalid role")
