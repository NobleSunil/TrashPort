"""
Admin-specific views for managing pickup requests, categories, complaints, and statistics.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from waste_management.models import Complaint, PickupRequest, WasteCategory, SubscriptionTier
from trashport.users.models import User
from .forms import WasteCategoryForm, SubscriptionTierForm


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Administrator Dashboard.
    Displays metrics (total pickups, pending requests, user totals),
    lists active complaints, recent pickup requests, waste categories, and subscription tiers.
    """
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role

        # Fetch aggregate counts and metrics for admin view
        context["total_pickups"] = PickupRequest.objects.count()
        context["pending_pickups"] = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.PENDING).count()
        context["active_complaints"] = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).count()
        context["total_citizens"] = User.objects.filter(role=User.Roles.CITIZEN).count()
        context["total_collectors"] = User.objects.filter(role=User.Roles.COLLECTOR).count()
        
        # Lists for the dashboard components
        context["complaints"] = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).order_by("-created_at")
        context["recent_pickups"] = PickupRequest.objects.all().order_by("-created_at")[:10]
        context["categories"] = WasteCategory.objects.all()
        context["tiers"] = SubscriptionTier.objects.all()

        return context


class AdminPickupRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Displays detail information for a pickup request to the Admin.
    Also provides a list of collectors for manual assignment.
    """
    model = PickupRequest
    template_name = "admin/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        return PickupRequest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Expose available collectors in context for manual assignment select dropdown
        context["collectors"] = User.objects.filter(role=User.Roles.COLLECTOR)
        return context


class AdminPickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Handles administrator-specific actions on a pickup request via POST.
    Supported actions:
    - assign: Manually assign a pickup request to a collector.
    - cancel: Force-cancel a pickup request.
    """
    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        action = request.POST.get("action")

        if action == "assign":
            collector_id = request.POST.get("collector")
            if collector_id:
                collector = get_object_or_404(User, pk=collector_id, role=User.Roles.COLLECTOR)
                pickup.collector = collector
                pickup.status = PickupRequest.StatusChoices.ASSIGNED
                pickup.save()
                messages.success(request, f"Assigned to collector {collector.name or collector.email}")
        elif action == "cancel":
            pickup.status = PickupRequest.StatusChoices.CANCELLED
            pickup.save()
            messages.warning(request, "Pickup request cancelled by Admin.")

        return redirect("waste_management:pickup_detail", pk=pk)


class AdminComplaintListView(LoginRequiredMixin, ListView):
    """
    Lists all complaints registered in the system for admin review.
    """
    model = Complaint
    template_name = "admin/complaint_list.html"
    context_object_name = "complaints"

    def get_queryset(self):
        return Complaint.objects.all().order_by("-created_at")


class AdminComplaintDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a single complaint.
    Handles the POST action to resolve a pending complaint.
    """
    model = Complaint
    template_name = "admin/complaint_detail.html"
    context_object_name = "complaint"

    def get_queryset(self):
        return Complaint.objects.all()

    def post(self, request, pk, *args, **kwargs):
        complaint = get_object_or_404(Complaint, pk=pk)
        action = request.POST.get("action")
        if action == "resolve":
            complaint.status = Complaint.StatusChoices.RESOLVED
            complaint.save()
            messages.success(request, "Complaint marked as resolved.")
        return redirect("waste_management:complaint_detail", pk=pk)


# ==============================================================================
# Waste Category CRUD Views
# ==============================================================================

class WasteCategoryListView(LoginRequiredMixin, ListView):
    """
    Lists all waste categories and their pricing model.
    """
    model = WasteCategory
    template_name = "admin/category_list.html"
    context_object_name = "categories"


class WasteCategoryCreateView(LoginRequiredMixin, CreateView):
    """
    Allows Admins to register a new waste category with collection fee and points reward.
    """
    model = WasteCategory
    form_class = WasteCategoryForm
    template_name = "admin/category_form.html"
    success_url = reverse_lazy("waste_management:category_list")

    def form_valid(self, form):
        messages.success(self.request, "Waste Category created!")
        return super().form_valid(form)


class WasteCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows Admins to update an existing waste category (fee, points reward, description, name).
    """
    model = WasteCategory
    form_class = WasteCategoryForm
    template_name = "admin/category_form.html"
    success_url = reverse_lazy("waste_management:category_list")

    def form_valid(self, form):
        messages.success(self.request, "Waste Category updated!")
        return super().form_valid(form)


# ==============================================================================
# Subscription Tier CRUD Views
# ==============================================================================

class AdminSubscriptionTierListView(LoginRequiredMixin, ListView):
    model = SubscriptionTier
    template_name = "admin/tier_list.html"
    context_object_name = "tiers"


class AdminSubscriptionTierCreateView(LoginRequiredMixin, CreateView):
    model = SubscriptionTier
    form_class = SubscriptionTierForm
    template_name = "admin/tier_form.html"
    success_url = reverse_lazy("waste_management:tier_list")

    def form_valid(self, form):
        messages.success(self.request, "Subscription Tier created!")
        return super().form_valid(form)


class AdminSubscriptionTierUpdateView(LoginRequiredMixin, UpdateView):
    model = SubscriptionTier
    form_class = SubscriptionTierForm
    template_name = "admin/tier_form.html"
    success_url = reverse_lazy("waste_management:tier_list")

    def form_valid(self, form):
        messages.success(self.request, "Subscription Tier updated!")
        return super().form_valid(form)
