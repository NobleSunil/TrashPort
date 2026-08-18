"""
Admin-specific views for managing pickup requests, categories, complaints, and statistics.
"""

import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from trashport.users.models import User
from waste_management.models import Complaint, PickupRequest, Subscription, SubscriptionTier, WasteCategory
from .forms import CollectorCreationForm, SubscriptionTierForm, WalletPointAdjustmentForm, WasteCategoryForm


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Administrator Dashboard.
    Displays metrics (total pickups, revenue, recycled weight, completion rate),
    Chart.js visual statistics, dynamic filterable pickup requests, active complaints,
    waste categories, and subscription tiers.
    """
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role

        # Aggregate counts and metrics for admin view
        total_pickups = PickupRequest.objects.count()
        completed_pickups = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.COMPLETED).count()
        pending_pickups = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.PENDING).count()
        active_complaints = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).count()
        total_citizens = User.objects.filter(role=User.Roles.CITIZEN).count()
        total_collectors = User.objects.filter(role=User.Roles.COLLECTOR).count()

        total_revenue = PickupRequest.objects.filter(is_paid=True).aggregate(total=Sum("fee"))["total"] or 0
        total_weight_kg = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.COMPLETED).aggregate(total=Sum("weight_kg"))["total"] or 0
        total_points_earned = PickupRequest.objects.aggregate(total=Sum("points_earned"))["total"] or 0
        completion_rate = round((completed_pickups / total_pickups * 100), 1) if total_pickups > 0 else 0

        context["total_pickups"] = total_pickups
        context["completed_pickups"] = completed_pickups
        context["pending_pickups"] = pending_pickups
        context["active_complaints"] = active_complaints
        context["total_citizens"] = total_citizens
        context["total_collectors"] = total_collectors
        context["total_revenue"] = total_revenue
        context["total_weight_kg"] = total_weight_kg
        context["total_points_earned"] = total_points_earned
        context["completion_rate"] = completion_rate

        # Waste Category distribution for Doughnut Chart
        cat_stats = (
            PickupRequest.objects.values("category__name")
            .annotate(total_kg=Sum("weight_kg"), count=Count("id"))
            .order_by("-total_kg")
        )
        cat_labels = [item["category__name"] for item in cat_stats if item["category__name"]]
        cat_weights = [float(item["total_kg"] or 0) for item in cat_stats if item["category__name"]]

        # Status breakdown count
        status_stats = (
            PickupRequest.objects.values("status")
            .annotate(count=Count("id"))
        )
        status_counts = {s.value: 0 for s in PickupRequest.StatusChoices}
        for item in status_stats:
            status_counts[item["status"]] = item["count"]

        # Request volume trend over time
        trend_stats = (
            PickupRequest.objects.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")[:14]
        )
        trend_labels = [item["date"].strftime("%b %d") if item["date"] else "" for item in trend_stats]
        trend_counts = [item["count"] for item in trend_stats]

        context["cat_labels_json"] = json.dumps(cat_labels)
        context["cat_weights_json"] = json.dumps(cat_weights)
        context["status_counts_json"] = json.dumps(status_counts)
        context["trend_labels_json"] = json.dumps(trend_labels)
        context["trend_counts_json"] = json.dumps(trend_counts)

        # Dynamic Filters for Recent Pickups Table
        selected_status = self.request.GET.get("status", "").strip()
        search_query = self.request.GET.get("q", "").strip()

        pickups_qs = PickupRequest.objects.select_related("citizen", "address", "category", "collector").all().order_by("-created_at")

        if selected_status:
            pickups_qs = pickups_qs.filter(status=selected_status)
        if search_query:
            pickups_qs = pickups_qs.filter(
                Q(citizen__email__icontains=search_query)
                | Q(citizen__name__icontains=search_query)
                | Q(address__city__icontains=search_query)
            )

        context["recent_pickups"] = pickups_qs[:20]
        context["selected_status"] = selected_status
        context["search_query"] = search_query
        context["status_choices"] = PickupRequest.StatusChoices.choices

        # Dashboard components
        context["complaints"] = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).order_by("-created_at")
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


# ==============================================================================
# User Administration Views
# ==============================================================================

class AdminUserListView(LoginRequiredMixin, ListView):
    """
    Lists all users (Citizens, Collectors, Admins) with role filtering and search.
    """
    model = User
    template_name = "admin/user_list.html"
    context_object_name = "users_list"

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        role_filter = self.request.GET.get("role", "").strip()
        search_query = self.request.GET.get("q", "").strip()

        if role_filter:
            qs = qs.filter(role=role_filter)
        if search_query:
            qs = qs.filter(
                Q(email__icontains=search_query) | Q(name__icontains=search_query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_role"] = self.request.GET.get("role", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["role_choices"] = User.Roles.choices
        return context


class AdminCollectorCreateView(LoginRequiredMixin, CreateView):
    """
    Allows Admins to register/onboard new Collector accounts.
    """
    model = User
    form_class = CollectorCreationForm
    template_name = "admin/collector_form.html"
    success_url = reverse_lazy("waste_management:user_list")

    def form_valid(self, form):
        messages.success(self.request, f"Collector account '{form.instance.email}' created successfully!")
        return super().form_valid(form)


class AdminUserDetailView(LoginRequiredMixin, DetailView):
    """
    Displays full details of a user including addresses, wallet points, and pickup history.
    """
    model = User
    template_name = "admin/user_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = self.object
        context["pickups"] = PickupRequest.objects.filter(
            Q(citizen=target) | Q(collector=target)
        ).select_related("category", "address").order_by("-created_at")[:20]
        context["addresses"] = target.addresses.all() if hasattr(target, "addresses") else []
        context["wallet_form"] = WalletPointAdjustmentForm()
        return context


class AdminUserToggleActiveView(LoginRequiredMixin, View):
    """
    POST action to suspend or reactivate a user account.
    """
    def post(self, request, pk, *args, **kwargs):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("waste_management:user_detail", pk=pk)

        target.is_active = not target.is_active
        target.save()
        status_str = "activated" if target.is_active else "suspended"
        messages.success(request, f"User {target.email} has been {status_str}.")
        return redirect("waste_management:user_detail", pk=pk)


class AdminWalletAdjustView(LoginRequiredMixin, View):
    """
    POST action to credit or debit recycling wallet points for a citizen.
    """
    def post(self, request, pk, *args, **kwargs):
        target = get_object_or_404(User, pk=pk)
        form = WalletPointAdjustmentForm(request.POST)
        if form.is_valid():
            points = form.cleaned_data["points"]
            reason = form.cleaned_data.get("reason", "")
            target.wallet_points += points
            if target.wallet_points < 0:
                target.wallet_points = 0
            target.save()
            reason_msg = f" ({reason})" if reason else ""
            messages.success(request, f"Adjusted wallet points by {points:+d} for {target.email}{reason_msg}.")
        else:
            messages.error(request, "Invalid point adjustment input.")
        return redirect("waste_management:user_detail", pk=pk)


# ==============================================================================
# Smart Dispatch & Auto-Assignment View
# ==============================================================================

class AdminAutoAssignPickupsView(LoginRequiredMixin, View):
    """
    Auto-assigns all PENDING pickup requests to available collectors,
    balancing workloads across active collectors.
    """
    def post(self, request, *args, **kwargs):
        pending_pickups = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.PENDING)
        collectors = list(User.objects.filter(role=User.Roles.COLLECTOR, is_active=True))

        if not collectors:
            messages.error(request, "No active collectors available for assignment.")
            return redirect("waste_management:dashboard")

        assigned_count = 0
        collector_idx = 0
        num_collectors = len(collectors)

        for pickup in pending_pickups:
            chosen_collector = collectors[collector_idx % num_collectors]
            pickup.collector = chosen_collector
            pickup.status = PickupRequest.StatusChoices.ASSIGNED
            pickup.save()
            assigned_count += 1
            collector_idx += 1

        messages.success(request, f"Auto-assigned {assigned_count} pending pickup requests across {num_collectors} collectors!")
        return redirect("waste_management:dashboard")


# ==============================================================================
# Subscriptions Overview View
# ==============================================================================

class AdminSubscriptionOverviewView(LoginRequiredMixin, ListView):
    """
    Displays all active citizen subscriptions.
    """
    model = Subscription
    template_name = "admin/subscription_overview.html"
    context_object_name = "subscriptions"

    def get_queryset(self):
        return Subscription.objects.select_related("user", "tier").all().order_by("-created_at")


# ==============================================================================
# Data Export Views (CSV Output)
# ==============================================================================

import csv
from django.http import HttpResponse


class AdminExportPickupsCSVView(LoginRequiredMixin, View):
    """
    Generates a CSV report of all pickup requests in the system.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="trashport_pickups_report.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Customer Email", "Customer Name", "City", "Category", "Weight (kg)", "Fee (Rs.)", "Points", "Status", "Collector", "Schedule Date", "Created At"])

        pickups = PickupRequest.objects.select_related("citizen", "address", "category", "collector").all().order_by("-created_at")
        for p in pickups:
            writer.writerow([
                p.id,
                p.citizen.email,
                p.citizen.name or "",
                p.address.city if p.address else "",
                p.category.name if p.category else "",
                p.weight_kg,
                p.fee,
                p.points_earned,
                p.status,
                p.collector.email if p.collector else "Unassigned",
                p.schedule_date.strftime("%Y-%m-%d %H:%M"),
                p.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
        return response


class AdminExportRevenueCSVView(LoginRequiredMixin, View):
    """
    Generates a CSV financial report summarizing paid collection fees and category totals.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="trashport_revenue_report.csv"'

        writer = csv.writer(response)
        writer.writerow(["Category", "Total Completed Pickups", "Total Recycled Weight (kg)", "Total Revenue (Rs.)", "Total Points Rewarded"])

        cats = WasteCategory.objects.all()
        for c in cats:
            completed_qs = PickupRequest.objects.filter(category=c, status=PickupRequest.StatusChoices.COMPLETED)
            paid_qs = PickupRequest.objects.filter(category=c, is_paid=True)

            count = completed_qs.count()
            weight = completed_qs.aggregate(total=Sum("weight_kg"))["total"] or 0
            revenue = paid_qs.aggregate(total=Sum("fee"))["total"] or 0
            points = PickupRequest.objects.filter(category=c).aggregate(total=Sum("points_earned"))["total"] or 0

            writer.writerow([c.name, count, weight, revenue, points])
        return response

