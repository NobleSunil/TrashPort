"""
Admin-specific views for managing pickup requests, categories, complaints, and statistics.
=========================================================================================

PURPOSE:
  This file contains ALL view classes that are exclusively used by Administrator users.
  Each view is dispatched to from waste_management/views.py via the RoleDispatchView
  system, which checks user.role == ADMIN before forwarding here.

CONNECTION MAP:
  - waste_management/views.py   → dispatches to views in this file (DashboardView, etc.)
  - waste_management/urls.py    → URL endpoints resolve through the dispatchers above
  - trashport/admins/urls.py    → API-scoped admin routes (live map, reports)
  - trashport/admins/forms.py   → form classes used by create/update views here
  - waste_management/models.py  → PickupRequest, WasteCategory, Complaint, CollectorPayoutSetting
  - trashport/payments/models.py → UPIPayoutRequest for payout history

IMPACT:
  - Adding a new admin feature: create the view class here, then add a dispatcher
    in waste_management/views.py and register the URL in waste_management/urls.py.
  - Modifying aggregation queries affects dashboard KPI cards and Chart.js graphs.
  - CSV export views directly stream to browser — changes affect downloaded files.
"""

import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from trashport.services.payments.models import UPIPayoutRequest
from trashport.users.models import User
from trashport.core.waste_management.models import (
    AnonymousFeedback,
    CollectorPayoutSetting,
    Complaint,
    PickupRequest,
    WasteCategory,
    City,
    Hub,
    Vehicle,
    Route,
    RoutePickup,
)
from .forms import (
    CollectorCreationForm,
    CollectorPayoutSettingForm,
    WalletPointAdjustmentForm,
    WasteCategoryForm,
    CityForm,
    HubForm,
    VehicleForm,
    RouteForm,
)


class AdminLiveMapView(LoginRequiredMixin, TemplateView):
    """
    Renders the Control Room Live Map for Administrators.
    Displays all active citizen pickup locations and live moving collector GPS coordinates in real-time.
    """
    template_name = "admin/live_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role"] = self.request.user.role
        return context


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
        total_collector_payouts = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.COMPLETED).aggregate(total=Sum("collector_earnings"))["total"] or 0
        total_extra_charges = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.COMPLETED).aggregate(total=Sum("extra_fee"))["total"] or 0

        total_upi_redeemed = UPIPayoutRequest.objects.filter(status=UPIPayoutRequest.Statuses.COMPLETED).aggregate(total=Sum("amount"))["total"] or 0

        # Dynamic Filters & Limit for UPI Payouts Table
        payout_per_page = self.request.GET.get("payout_per_page", "5").strip()
        payouts_qs = UPIPayoutRequest.objects.select_related("collector").order_by("-created_at")
        if payout_per_page == "all":
            context["recent_upi_payouts"] = payouts_qs
        else:
            try:
                p_limit = int(payout_per_page)
            except ValueError:
                p_limit = 5
            context["recent_upi_payouts"] = payouts_qs[:p_limit]
        context["payout_per_page"] = payout_per_page
        context["total_upi_redeemed"] = total_upi_redeemed

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
        context["total_collector_payouts"] = total_collector_payouts
        context["total_extra_charges"] = total_extra_charges
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

        # Dynamic Filters & Limits for Recent Pickups Table
        selected_status = self.request.GET.get("status", "").strip()
        search_query = self.request.GET.get("q", "").strip()
        per_page = self.request.GET.get("per_page", "5").strip()

        pickups_qs = PickupRequest.objects.select_related("citizen", "address", "category", "collector").all().order_by("-created_at")

        if selected_status:
            pickups_qs = pickups_qs.filter(status=selected_status)
        if search_query:
            pickups_qs = pickups_qs.filter(
                Q(citizen__email__icontains=search_query)
                | Q(citizen__name__icontains=search_query)
                | Q(address__city__icontains=search_query)
            )

        if per_page == "all":
            context["recent_pickups"] = pickups_qs
        else:
            try:
                limit = int(per_page)
            except ValueError:
                limit = 5
            context["recent_pickups"] = pickups_qs[:limit]

        context["selected_status"] = selected_status
        context["search_query"] = search_query
        context["per_page"] = per_page

        # Dynamic Filters for Pending Complaints
        complaint_per_page = self.request.GET.get("complaint_per_page", "5").strip()
        complaints_qs = Complaint.objects.filter(
            status=Complaint.StatusChoices.PENDING
        ).select_related("citizen", "pickup_request").order_by("-created_at")

        if complaint_per_page == "all":
            context["complaints"] = complaints_qs
        else:
            try:
                c_limit = int(complaint_per_page)
            except ValueError:
                c_limit = 5
            context["complaints"] = complaints_qs[:c_limit]
        context["complaint_per_page"] = complaint_per_page

        context["categories"] = WasteCategory.objects.all()
        context["collector_payout_setting"] = CollectorPayoutSetting.get_settings()
        context["unreviewed_feedback_count"] = AnonymousFeedback.objects.filter(is_reviewed=False).count()
        context["recent_anonymous_feedbacks"] = AnonymousFeedback.objects.all().order_by("-created_at")[:6]

        # Hub Infrastructure for Dashboard Map & Interactive Operations
        all_hubs_qs = Hub.objects.select_related("city").prefetch_related("vehicles").all().order_by("city__name", "name")
        hubs_list_data = []
        for h in all_hubs_qs:
            hubs_list_data.append({
                "id": h.id,
                "name": h.name,
                "city": h.city.name,
                "city_id": h.city.id,
                "state": h.city.state,
                "lat": float(h.latitude),
                "lng": float(h.longitude),
                "address": h.address or "",
                "is_active": h.is_active,
                "vehicle_count": h.vehicles.count(),
                "edit_url": reverse("waste_management:hub_update", kwargs={"pk": h.id}),
                "toggle_url": reverse("waste_management:hub_toggle_active", kwargs={"pk": h.id}),
                "delete_url": reverse("waste_management:hub_delete", kwargs={"pk": h.id}),
            })
        context["dashboard_hubs"] = all_hubs_qs
        context["dashboard_hubs_json"] = json.dumps(hubs_list_data)
        context["total_hubs_count"] = len(hubs_list_data)
        context["active_hubs_count"] = sum(1 for h in hubs_list_data if h["is_active"])
        context["suspended_hubs_count"] = sum(1 for h in hubs_list_data if not h["is_active"])

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
        context["payout_settings"] = CollectorPayoutSetting.get_settings()
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



class AdminAnonymousFeedbackListView(LoginRequiredMixin, ListView):
    """
    Lists all anonymous feedback submissions received from visitors and citizens for admin review.
    """
    model = AnonymousFeedback
    template_name = "admin/anonymous_feedback_list.html"
    context_object_name = "feedbacks"

    def get_queryset(self):
        return AnonymousFeedback.objects.all().order_by("-created_at")

    def post(self, request, *args, **kwargs):
        feedback_id = request.POST.get("feedback_id")
        action = request.POST.get("action")
        if feedback_id and action == "toggle_review":
            fb = get_object_or_404(AnonymousFeedback, id=feedback_id)
            fb.is_reviewed = not fb.is_reviewed
            fb.save()
            status_text = "reviewed" if fb.is_reviewed else "unreviewed"
            messages.success(request, f"Feedback #{fb.id} marked as {status_text}.")
        elif feedback_id and action == "delete":
            fb = get_object_or_404(AnonymousFeedback, id=feedback_id)
            fb.delete()
            messages.success(request, "Feedback entry deleted.")
        return redirect("waste_management:anonymous_feedback_list")



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
# Collector Payout Settings View
# ==============================================================================


class CollectorPayoutSettingUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows Admins to view and configure collector payout rules:
    - Base minimum payout (Rs.)
    - Rate per kilometer (Rs./km)
    - Extra weight commission percentage (%)
    """
    model = CollectorPayoutSetting
    form_class = CollectorPayoutSettingForm
    template_name = "admin/payout_settings_form.html"
    success_url = reverse_lazy("waste_management:collector_payout_settings")

    def get_object(self, queryset=None):
        return CollectorPayoutSetting.get_settings()

    def form_valid(self, form):
        messages.success(self.request, "Collector payout calculation settings successfully updated!")
        return super().form_valid(form)



# ==============================================================================
# User Administration Views
# ==============================================================================

class AdminUserListView(LoginRequiredMixin, ListView):
    """
    Lists all users (Citizens, Collectors, Admins) with role filtering,
    verified vs unverified sorting & filtering, and search.
    """
    model = User
    template_name = "admin/user_list.html"
    context_object_name = "users_list"

    def get_queryset(self):
        qs = User.objects.all()
        role_filter = self.request.GET.get("role", "").strip()
        verification_filter = self.request.GET.get("verification", "").strip()
        is_verified_filter = self.request.GET.get("is_verified", "").strip()
        sort_by = self.request.GET.get("sort", "").strip()
        search_query = self.request.GET.get("q", "").strip()

        if role_filter:
            qs = qs.filter(role=role_filter)
        if verification_filter:
            qs = qs.filter(verification_status=verification_filter)
        if is_verified_filter in ["true", "1"]:
            qs = qs.filter(verification_status=User.VerificationStatus.APPROVED)
        elif is_verified_filter in ["false", "0"]:
            qs = qs.exclude(verification_status=User.VerificationStatus.APPROVED)

        if search_query:
            qs = qs.filter(
                Q(email__icontains=search_query) | Q(name__icontains=search_query)
            )

        # Sorting logic
        if sort_by == "verified_first":
            qs = qs.order_by("-verification_status", "-date_joined")
        elif sort_by == "unverified_first":
            qs = qs.order_by("verification_status", "-date_joined")
        elif sort_by == "name":
            qs = qs.order_by("name", "email")
        else:
            qs = qs.order_by("-date_joined")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_role"] = self.request.GET.get("role", "")
        context["selected_verification"] = self.request.GET.get("verification", "")
        context["selected_is_verified"] = self.request.GET.get("is_verified", "")
        context["selected_sort"] = self.request.GET.get("sort", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["role_choices"] = User.Roles.choices
        context["verification_choices"] = User.VerificationStatus.choices
        context["pending_collectors_count"] = User.objects.filter(
            role=User.Roles.COLLECTOR,
            verification_status=User.VerificationStatus.PENDING
        ).count()
        context["verified_collectors_count"] = User.objects.filter(
            role=User.Roles.COLLECTOR,
            verification_status=User.VerificationStatus.APPROVED
        ).count()
        context["unverified_collectors_count"] = User.objects.filter(
            role=User.Roles.COLLECTOR
        ).exclude(
            verification_status=User.VerificationStatus.APPROVED
        ).count()
        context["total_citizens_count"] = User.objects.filter(
            role=User.Roles.CITIZEN
        ).count()
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
        collector = form.save(commit=False)
        collector.role = User.Roles.COLLECTOR
        collector.is_verified = True
        collector.verification_status = User.VerificationStatus.APPROVED
        collector.save()
        messages.success(self.request, f"Verified Collector account '{collector.email}' created successfully!")
        return redirect(self.success_url)


class AdminUserDetailView(LoginRequiredMixin, DetailView):
    """
    Displays full details of a user including addresses, wallet points, collector earnings, UPI payouts, and pickup history.
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
        if target.role == User.Roles.COLLECTOR:
            completed_qs = PickupRequest.objects.filter(collector=target, status=PickupRequest.StatusChoices.COMPLETED)
            context["collector_completed_count"] = completed_qs.count()
            context["collector_total_weight"] = completed_qs.aggregate(total=Sum("weight_kg"))["total"] or 0
            context["collector_total_earnings"] = completed_qs.aggregate(total=Sum("collector_earnings"))["total"] or 0
            context["upi_payouts"] = UPIPayoutRequest.objects.filter(collector=target).order_by("-created_at")
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


class AdminUserDeleteView(LoginRequiredMixin, View):
    """
    POST action for Admins to permanently delete a user account from the system.

    Enforces enterprise security and operational safeguards:
    1. Administrator authorization check (ADMIN role, staff, or superuser).
    2. Prevention of self-deletion (an admin cannot delete their own active session).
    3. Privilege escalation guard (non-superusers cannot delete superusers).
    4. Active operations check:
       - Collector: blocks deletion if collector has active pickups (ASSIGNED, ON_THE_WAY, ARRIVED).
       - Citizen: blocks deletion if citizen has pickups actively in transit.
    5. Clean fleet detachment: automatically unassigns collector from any Vehicles.
    6. Cascade deletion of associated non-operational profiles and records.
    """
    def post(self, request, pk, *args, **kwargs):
        # 1. Enforce administrator role check
        if not (request.user.role == User.Roles.ADMIN or request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission denied. Administrator access required.")
            return redirect("waste_management:user_list")

        target = get_object_or_404(User, pk=pk)

        # 2. Cannot delete own account
        if target == request.user:
            messages.error(request, "Security violation: You cannot delete your own administrator account.")
            return redirect("waste_management:user_detail", pk=pk)

        # 3. Non-superusers cannot delete superusers
        if target.is_superuser and not request.user.is_superuser:
            messages.error(request, "Permission denied: Only superusers can delete other superuser accounts.")
            return redirect("waste_management:user_detail", pk=pk)

        user_identifier = target.name or target.email

        # 4. Check for active in-progress pickups for collectors
        if target.role == User.Roles.COLLECTOR:
            active_collector_pickups = PickupRequest.objects.filter(
                collector=target,
                status__in=[
                    PickupRequest.StatusChoices.ASSIGNED,
                    PickupRequest.StatusChoices.IN_TRANSIT,
                    PickupRequest.StatusChoices.ON_ROUTE,
                    PickupRequest.StatusChoices.PICKED_UP,
                ]
            ).count()
            if active_collector_pickups > 0:
                messages.error(
                    request,
                    f"Cannot delete Collector '{user_identifier}' because they have {active_collector_pickups} active in-progress pickup(s). Please reassign or complete those pickups first."
                )
                return redirect("waste_management:user_detail", pk=pk)

            # Safely release collector from any assigned fleet vehicles
            Vehicle.objects.filter(driver=target).update(driver=None, status=Vehicle.StatusChoices.AVAILABLE)

        elif target.role == User.Roles.CITIZEN:
            active_citizen_pickups = PickupRequest.objects.filter(
                citizen=target,
                status__in=[
                    PickupRequest.StatusChoices.ASSIGNED,
                    PickupRequest.StatusChoices.IN_TRANSIT,
                    PickupRequest.StatusChoices.ON_ROUTE,
                    PickupRequest.StatusChoices.PICKED_UP,
                ]
            ).count()
            if active_citizen_pickups > 0:
                messages.error(
                    request,
                    f"Cannot delete Citizen '{user_identifier}' because they have {active_citizen_pickups} active pickup(s) currently being serviced. Please resolve or cancel those pickups first."
                )
                return redirect("waste_management:user_detail", pk=pk)

        # 5. Execute permanent deletion
        target.delete()
        messages.success(request, f"User account '{user_identifier}' has been permanently deleted.")
        return redirect("waste_management:user_list")



class AdminCollectorVerificationView(LoginRequiredMixin, View):
    """
    POST action for Admins to Approve or Reject a Collector's account verification.
    """
    def post(self, request, pk, *args, **kwargs):
        collector = get_object_or_404(User, pk=pk, role=User.Roles.COLLECTOR)
        action = request.POST.get("action")  # "approve" or "reject"

        if action == "approve":
            collector.is_verified = True
            collector.verification_status = User.VerificationStatus.APPROVED
            collector.save()
            messages.success(request, f"Collector '{collector.name or collector.email}' has been approved and verified!")
        elif action == "reject":
            collector.is_verified = False
            collector.verification_status = User.VerificationStatus.REJECTED
            collector.save()
            messages.warning(request, f"Collector '{collector.name or collector.email}' verification has been rejected.")

        next_url = request.POST.get("next") or reverse_lazy("waste_management:user_list")
        return redirect(next_url)


class AdminWalletAdjustView(LoginRequiredMixin, View):
    """
    POST action to credit or debit recycling wallet points for a citizen,
    or cash balance for a collector.
    """
    def post(self, request, pk, *args, **kwargs):

        target = get_object_or_404(User, pk=pk)

        # Check if collector cash adjustment or citizen point adjustment
        cash_amount = request.POST.get("cash_amount")
        if cash_amount and target.role == User.Roles.COLLECTOR:
            try:
                amt = Decimal(cash_amount)
                target.wallet_balance += amt
                if target.wallet_balance < 0:
                    target.wallet_balance = Decimal("0.00")
                target.save()
                messages.success(request, f"Adjusted collector wallet balance by Rs. {amt:+.2f} for {target.email}.")
            except Exception as e:
                messages.error(request, f"Invalid cash amount: {e}")
            return redirect("waste_management:user_detail", pk=pk)

        form = WalletPointAdjustmentForm(request.POST)
        if form.is_valid():
            points = form.cleaned_data["points"]
            reason = form.cleaned_data.get("reason", "").strip()
            from trashport.services.payments.services import WalletService
            WalletService.adjust_points(
                user=target,
                points_delta=points,
                reason=reason or f"Admin point adjustment ({points:+d} pts)"
            )
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
# Shared Date Range Parsing Helper
# ==============================================================================
#
# PURPOSE:
#   Parses duration presets (today, yesterday, 7days, 30days, this_month,
#   last_month, year, all) or custom start_date/end_date query parameters
#   from an HTTP request into a normalized (duration, start_date, end_date) tuple.
#
# CONNECTIONS:
#   - Used by: AdminOperationsReportView.get_context_data()
#   - Can be reused by any admin view needing duration-based date filtering.
#
# RETURNS:
#   Tuple of (duration: str, start_date: date|None, end_date: date|None)
# ==============================================================================

def _parse_date_range(request):
    """Parse duration presets or custom date range from GET parameters."""
    today = timezone.localdate()
    duration = request.GET.get("duration", "").strip()
    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()

    start_date = None
    end_date = None

    if start_date_str or end_date_str:
        duration = "custom"
        if start_date_str:
            start_date = parse_date(start_date_str)
        if end_date_str:
            end_date = parse_date(end_date_str)
    elif duration == "today":
        start_date = today
        end_date = today
    elif duration == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif duration == "7days":
        start_date = today - timedelta(days=6)
        end_date = today
    elif duration == "30days":
        start_date = today - timedelta(days=29)
        end_date = today
    elif duration == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif duration == "last_month":
        first_day_current_month = today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)
        end_date = last_day_last_month
    elif duration == "year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif duration == "all":
        start_date = None
        end_date = None
    else:
        duration = "30days"
        start_date = today - timedelta(days=29)
        end_date = today

    return duration, start_date, end_date


# ==============================================================================
# Operations & Analytics Report View
# ==============================================================================

class AdminOperationsReportView(LoginRequiredMixin, TemplateView):
    """
    Renders comprehensive operations and financial analytics report for administrators.
    Supports custom duration selection (presets or start/end date pickers),
    computes key performance indicators, generates multi-dimensional Chart.js visual graphs,
    and provides dedicated print/PDF styling and duration-filtered CSV exports.
    """
    template_name = "admin/operations_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role

        today = timezone.localdate()
        duration, start_date, end_date = _parse_date_range(self.request)

        context["duration"] = duration
        context["start_date"] = start_date.strftime("%Y-%m-%d") if start_date else ""
        context["end_date"] = end_date.strftime("%Y-%m-%d") if end_date else ""
        context["today"] = today.strftime("%Y-%m-%d")
        context["generated_at"] = timezone.now()

        # Date range human-readable display
        if duration == "all":
            context["date_range_display"] = "All Time"
        elif start_date and end_date:
            if start_date == end_date:
                context["date_range_display"] = start_date.strftime("%B %d, %Y")
            else:
                context["date_range_display"] = f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
        elif start_date:
            context["date_range_display"] = f"From {start_date.strftime('%b %d, %Y')}"
        elif end_date:
            context["date_range_display"] = f"Until {end_date.strftime('%b %d, %Y')}"
        else:
            context["date_range_display"] = "All Time"

        # Filter base querysets
        pickups_qs = PickupRequest.objects.all()
        complaints_qs = Complaint.objects.all()

        if start_date:
            pickups_qs = pickups_qs.filter(created_at__date__gte=start_date)
            complaints_qs = complaints_qs.filter(created_at__date__gte=start_date)
        if end_date:
            pickups_qs = pickups_qs.filter(created_at__date__lte=end_date)
            complaints_qs = complaints_qs.filter(created_at__date__lte=end_date)

        # Operational KPIs
        total_pickups = pickups_qs.count()
        completed_pickups = pickups_qs.filter(status=PickupRequest.StatusChoices.COMPLETED).count()
        cancelled_pickups = pickups_qs.filter(status=PickupRequest.StatusChoices.CANCELLED).count()
        pending_pickups = pickups_qs.filter(status=PickupRequest.StatusChoices.PENDING).count()
        in_progress_pickups = pickups_qs.filter(
            status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]
        ).count()
        completion_rate = round((completed_pickups / total_pickups * 100), 1) if total_pickups > 0 else 0

        total_weight_kg = pickups_qs.filter(status=PickupRequest.StatusChoices.COMPLETED).aggregate(total=Sum("weight_kg"))["total"] or 0
        total_revenue = pickups_qs.filter(is_paid=True).aggregate(total=Sum("fee"))["total"] or 0
        total_collector_payouts = pickups_qs.filter(status=PickupRequest.StatusChoices.COMPLETED).aggregate(total=Sum("collector_earnings"))["total"] or 0
        total_points_earned = pickups_qs.aggregate(total=Sum("points_earned"))["total"] or 0
        net_margin = float(total_revenue) - float(total_collector_payouts)

        total_complaints = complaints_qs.count()
        resolved_complaints = complaints_qs.filter(status=Complaint.StatusChoices.RESOLVED).count()

        context["total_pickups"] = total_pickups
        context["completed_pickups"] = completed_pickups
        context["cancelled_pickups"] = cancelled_pickups
        context["pending_pickups"] = pending_pickups
        context["in_progress_pickups"] = in_progress_pickups
        context["completion_rate"] = completion_rate
        context["total_weight_kg"] = float(total_weight_kg)
        context["total_revenue"] = float(total_revenue)
        context["total_collector_payouts"] = float(total_collector_payouts)
        context["net_margin"] = float(net_margin)
        context["total_points_earned"] = total_points_earned
        context["total_complaints"] = total_complaints
        context["resolved_complaints"] = resolved_complaints

        # Category Performance Breakdown
        categories = WasteCategory.objects.all()
        category_report = []
        for cat in categories:
            cat_pickups = pickups_qs.filter(category=cat)
            cat_completed = cat_pickups.filter(status=PickupRequest.StatusChoices.COMPLETED)
            cat_paid = cat_pickups.filter(is_paid=True)

            c_count = cat_pickups.count()
            c_completed_count = cat_completed.count()
            c_weight = float(cat_completed.aggregate(total=Sum("weight_kg"))["total"] or 0)
            c_revenue = float(cat_paid.aggregate(total=Sum("fee"))["total"] or 0)
            c_payout = float(cat_completed.aggregate(total=Sum("collector_earnings"))["total"] or 0)
            c_margin = c_revenue - c_payout

            category_report.append({
                "category": cat,
                "count": c_count,
                "completed": c_completed_count,
                "weight_kg": c_weight,
                "revenue": c_revenue,
                "payout": c_payout,
                "margin": c_margin,
            })
        category_report.sort(key=lambda x: x["weight_kg"], reverse=True)
        context["category_report"] = category_report

        # Graph 1: Timeline Trend (Daily or Date Bins)
        days_span = (end_date - start_date).days + 1 if (start_date and end_date) else 30
        trend_labels = []
        trend_total_counts = []
        trend_completed_counts = []
        trend_revenues = []
        trend_payouts = []

        if start_date and end_date and days_span <= 62:
            date_cursor = start_date
            dates_list = []
            while date_cursor <= end_date:
                dates_list.append(date_cursor)
                date_cursor += timedelta(days=1)

            daily_stats = (
                pickups_qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(
                    total=Count("id"),
                    completed=Count("id", filter=Q(status=PickupRequest.StatusChoices.COMPLETED)),
                    revenue=Sum("fee", filter=Q(is_paid=True)),
                    payout=Sum("collector_earnings", filter=Q(status=PickupRequest.StatusChoices.COMPLETED)),
                )
            )
            daily_dict = {item["day"]: item for item in daily_stats if item["day"]}

            for d in dates_list:
                trend_labels.append(d.strftime("%b %d"))
                stat = daily_dict.get(d)
                if stat:
                    trend_total_counts.append(stat["total"])
                    trend_completed_counts.append(stat["completed"])
                    trend_revenues.append(float(stat["revenue"] or 0))
                    trend_payouts.append(float(stat["payout"] or 0))
                else:
                    trend_total_counts.append(0)
                    trend_completed_counts.append(0)
                    trend_revenues.append(0.0)
                    trend_payouts.append(0.0)
        else:
            daily_stats = (
                pickups_qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(
                    total=Count("id"),
                    completed=Count("id", filter=Q(status=PickupRequest.StatusChoices.COMPLETED)),
                    revenue=Sum("fee", filter=Q(is_paid=True)),
                    payout=Sum("collector_earnings", filter=Q(status=PickupRequest.StatusChoices.COMPLETED)),
                )
                .order_by("day")
            )
            for item in daily_stats:
                if item["day"]:
                    fmt = "%b %d, %Y" if days_span > 90 else "%b %d"
                    trend_labels.append(item["day"].strftime(fmt))
                    trend_total_counts.append(item["total"])
                    trend_completed_counts.append(item["completed"])
                    trend_revenues.append(float(item["revenue"] or 0))
                    trend_payouts.append(float(item["payout"] or 0))

        context["trend_labels_json"] = json.dumps(trend_labels)
        context["trend_total_counts_json"] = json.dumps(trend_total_counts)
        context["trend_completed_counts_json"] = json.dumps(trend_completed_counts)
        context["trend_revenues_json"] = json.dumps(trend_revenues)
        context["trend_payouts_json"] = json.dumps(trend_payouts)

        # Graph 2: Category Weight Distribution
        cat_labels = [item["category"].name for item in category_report if item["weight_kg"] > 0]
        cat_weights = [item["weight_kg"] for item in category_report if item["weight_kg"] > 0]
        if not cat_labels:
            cat_labels = [item["category"].name for item in category_report]
            cat_weights = [item["weight_kg"] for item in category_report]
        context["cat_labels_json"] = json.dumps(cat_labels)
        context["cat_weights_json"] = json.dumps(cat_weights)

        # Graph 3: Status Breakdown
        status_labels = ["Completed", "Assigned / In Transit", "Pending / Awaiting Payment", "Cancelled"]
        pending_and_payment = pending_pickups + pickups_qs.filter(status=PickupRequest.StatusChoices.AWAITING_PAYMENT).count()
        status_counts = [completed_pickups, in_progress_pickups, pending_and_payment, cancelled_pickups]
        context["status_labels_json"] = json.dumps(status_labels)
        context["status_counts_json"] = json.dumps(status_counts)

        # Table rows of recent pickups in this period (up to 100)
        context["recent_pickups"] = (
            pickups_qs.select_related("citizen", "address", "category", "collector")
            .order_by("-created_at")[:100]
        )
        return context


# ==============================================================================
# Data Export Views (CSV Output)
# ==============================================================================


class AdminExportPickupsCSVView(LoginRequiredMixin, View):
    """
    Generates a CSV report of pickup requests in the system, optionally filtered by date range.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="trashport_pickups_report.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Customer Email", "Customer Name", "City", "Category", "Weight (kg)", "Fee (Rs.)", "Points", "Status", "Collector", "Schedule Date", "Created At"])

        pickups = PickupRequest.objects.select_related("citizen", "address", "category", "collector").all()

        start_date_str = request.GET.get("start_date", "").strip()
        end_date_str = request.GET.get("end_date", "").strip()
        if start_date_str:
            s_date = parse_date(start_date_str)
            if s_date:
                pickups = pickups.filter(created_at__date__gte=s_date)
        if end_date_str:
            e_date = parse_date(end_date_str)
            if e_date:
                pickups = pickups.filter(created_at__date__lte=e_date)

        pickups = pickups.order_by("-created_at")
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
    Generates a CSV financial report summarizing collection fees and category totals,
    optionally filtered by date range.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="trashport_revenue_report.csv"'

        writer = csv.writer(response)
        writer.writerow(["Category", "Total Pickups", "Completed Pickups", "Total Recycled Weight (kg)", "Total Revenue (Rs.)", "Collector Payouts (Rs.)", "Net Margin (Rs.)", "Total Points Rewarded"])

        start_date_str = request.GET.get("start_date", "").strip()
        end_date_str = request.GET.get("end_date", "").strip()
        s_date = parse_date(start_date_str) if start_date_str else None
        e_date = parse_date(end_date_str) if end_date_str else None

        cats = WasteCategory.objects.all()
        for c in cats:
            qs = PickupRequest.objects.filter(category=c)
            if s_date:
                qs = qs.filter(created_at__date__gte=s_date)
            if e_date:
                qs = qs.filter(created_at__date__lte=e_date)

            total_count = qs.count()
            completed_qs = qs.filter(status=PickupRequest.StatusChoices.COMPLETED)
            paid_qs = qs.filter(is_paid=True)

            completed_count = completed_qs.count()
            weight = completed_qs.aggregate(total=Sum("weight_kg"))["total"] or 0
            revenue = paid_qs.aggregate(total=Sum("fee"))["total"] or 0
            payout = completed_qs.aggregate(total=Sum("collector_earnings"))["total"] or 0
            margin = float(revenue) - float(payout)
            points = qs.aggregate(total=Sum("points_earned"))["total"] or 0

            writer.writerow([c.name, total_count, completed_count, weight, revenue, payout, margin, points])
        return response


# ==============================================================================
# Admin Fleet, Hub, City & Route Operations Views
# ==============================================================================

class CityListView(LoginRequiredMixin, ListView):
    model = City
    template_name = "admin/city_list.html"
    context_object_name = "cities"
    ordering = ["name"]


class CityCreateView(LoginRequiredMixin, CreateView):
    model = City
    form_class = CityForm
    template_name = "admin/city_form.html"
    success_url = reverse_lazy("waste_management:city_list")

    def form_valid(self, form):
        messages.success(self.request, f"City '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class CityUpdateView(LoginRequiredMixin, UpdateView):
    model = City
    form_class = CityForm
    template_name = "admin/city_form.html"
    success_url = reverse_lazy("waste_management:city_list")

    def form_valid(self, form):
        messages.success(self.request, f"City '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class CityToggleActiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        city = get_object_or_404(City, pk=pk)
        city.is_active = not city.is_active
        city.save(update_fields=["is_active"])
        messages.success(request, f"City '{city.name}' status set to {'Active' if city.is_active else 'Inactive'}.")
        return redirect("waste_management:city_list")


class HubListView(LoginRequiredMixin, ListView):
    """
    Administrator Hub and Terminal management view.
    Supports server-side text search (name, city, address) and operational status filtering.
    """
    model = Hub
    template_name = "admin/hub_list.html"
    context_object_name = "hubs"

    def get_queryset(self):
        qs = Hub.objects.select_related("city").order_by("city__name", "name")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(city__name__icontains=q)
                | Q(city__state__icontains=q)
                | Q(address__icontains=q)
            )
        status_filter = self.request.GET.get("status", "").strip().lower()
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["status_filter"] = self.request.GET.get("status", "").strip().lower()
        context["total_hubs_count"] = Hub.objects.count()
        context["active_hubs_count"] = Hub.objects.filter(is_active=True).count()
        context["inactive_hubs_count"] = Hub.objects.filter(is_active=False).count()

        # Serialize all hubs for interactive network map visualization and adding hubs directly from map
        hubs_list_data = []
        for h in Hub.objects.select_related("city").all():
            hubs_list_data.append({
                "id": h.id,
                "name": h.name,
                "city": h.city.name,
                "city_id": h.city.id,
                "state": h.city.state,
                "lat": float(h.latitude),
                "lng": float(h.longitude),
                "address": h.address or "",
                "is_active": h.is_active,
                "vehicle_count": h.vehicles.count(),
                "edit_url": reverse("waste_management:hub_update", kwargs={"pk": h.id}),
            })
        context["hubs_json"] = json.dumps(hubs_list_data)
        return context


class HubCreateView(LoginRequiredMixin, CreateView):
    """
    Administrator-only view to create an operational collection hub.
    Supports interactive map-based location selection, dynamic 20km service radius preview,
    and automatic pre-population from URL query parameters (lat, lng, address, city).
    """
    model = Hub
    form_class = HubForm
    template_name = "admin/hub_form.html"
    success_url = reverse_lazy("waste_management:hub_list")

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == User.Roles.ADMIN or request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission denied. Administrator access required.")
            return redirect("waste_management:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        lat = self.request.GET.get("lat")
        lng = self.request.GET.get("lng")
        address = self.request.GET.get("address")
        city_param = self.request.GET.get("city")
        if lat:
            try:
                initial["latitude"] = Decimal(lat)
            except Exception:
                pass
        if lng:
            try:
                initial["longitude"] = Decimal(lng)
            except Exception:
                pass
        if address:
            initial["address"] = address
        if city_param:
            try:
                initial["city"] = int(city_param)
                initial["city_entry_mode"] = "select"
            except (ValueError, TypeError):
                # City name passed as string (e.g. from reverse geocode or map click)
                city_obj = City.objects.filter(name__iexact=city_param.strip()).first()
                if city_obj:
                    initial["city"] = city_obj.id
                    initial["city_entry_mode"] = "select"
                else:
                    initial["manual_city"] = city_param.strip()
                    initial["city_entry_mode"] = "manual"
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass existing hubs for visual context and coverage overlap analysis on the map
        hubs_data = []
        for h in Hub.objects.select_related("city").all():
            hubs_data.append({
                "id": h.id,
                "name": h.name,
                "city": h.city.name,
                "lat": float(h.latitude),
                "lng": float(h.longitude),
                "is_active": h.is_active,
            })
        context["existing_hubs_json"] = json.dumps(hubs_data)
        context["next_url"] = self.request.GET.get("next") or self.request.POST.get("next") or ""
        return context

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("waste_management:hub_list")

    def form_valid(self, form):
        messages.success(self.request, f"Hub '{form.instance.name}' registered successfully.")
        return super().form_valid(form)


class HubUpdateView(LoginRequiredMixin, UpdateView):
    """
    Administrator-only view to edit an existing Hub facility.
    Displays an interactive Leaflet map to adjust location coordinates and inspect the 20km radius.
    """
    model = Hub
    form_class = HubForm
    template_name = "admin/hub_form.html"
    success_url = reverse_lazy("waste_management:hub_list")

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == User.Roles.ADMIN or request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission denied. Administrator access required.")
            return redirect("waste_management:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass other existing hubs for visual context and coverage overlap analysis
        hubs_data = []
        current_hub_id = self.object.id if self.object else None
        for h in Hub.objects.select_related("city").all():
            if h.id == current_hub_id:
                continue
            hubs_data.append({
                "id": h.id,
                "name": h.name,
                "city": h.city.name,
                "lat": float(h.latitude),
                "lng": float(h.longitude),
                "is_active": h.is_active,
            })
        context["existing_hubs_json"] = json.dumps(hubs_data)
        context["next_url"] = self.request.GET.get("next") or self.request.POST.get("next")
        return context

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("waste_management:hub_list")

    def form_valid(self, form):
        messages.success(self.request, f"Hub '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class HubToggleActiveView(LoginRequiredMixin, View):
    """Toggle a Hub between Active (Operational) and Temporarily Suspended."""
    def post(self, request, pk):
        hub = get_object_or_404(Hub, pk=pk)
        hub.is_active = not hub.is_active
        hub.save(update_fields=["is_active"])
        status_label = "Active (Operational)" if hub.is_active else "Temporarily Suspended"
        messages.success(request, f"Hub '{hub.name}' status set to {status_label}.")
        next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
        if next_url:
            return redirect(next_url)
        return redirect("waste_management:hub_list")


class HubDeleteView(LoginRequiredMixin, View):
    """
    Administrator-only view to delete an operational Hub.
    Prevents deletion if there are active in-progress trip routes originating from this hub.
    """
    def post(self, request, pk):
        # Enforce administrator privileges
        if not (request.user.role == User.Roles.ADMIN or request.user.is_staff):
            messages.error(request, "Permission denied. Administrator access required.")
            return redirect("waste_management:hub_list")

        hub = get_object_or_404(Hub, pk=pk)
        hub_name = hub.name
        next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")

        # Check for active non-completed trip routes
        active_routes_count = hub.routes.filter(
            status__in=[Route.StatusChoices.PLANNED, Route.StatusChoices.ACTIVE]
        ).count()
        if active_routes_count > 0:
            messages.error(
                request,
                f"Cannot delete Hub '{hub_name}' because it currently has {active_routes_count} active in-progress trip route(s). Please complete or cancel those routes first, or set the hub to Temporarily Suspended."
            )
            if next_url:
                return redirect(next_url)
            return redirect("waste_management:hub_list")

        hub.delete()
        messages.success(request, f"Hub '{hub_name}' and its facility configuration have been deleted.")
        if next_url:
            return redirect(next_url)
        return redirect("waste_management:hub_list")


class VehicleListView(LoginRequiredMixin, ListView):
    model = Vehicle
    template_name = "admin/vehicle_list.html"
    context_object_name = "vehicles"
    queryset = Vehicle.objects.select_related("hub", "driver", "hub__city").order_by("hub__name", "vehicle_number")


class VehicleCreateView(LoginRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "admin/vehicle_form.html"
    success_url = reverse_lazy("waste_management:vehicle_list")

    def form_valid(self, form):
        messages.success(self.request, f"Vehicle '{form.instance.vehicle_number}' registered successfully.")
        return super().form_valid(form)


class VehicleUpdateView(LoginRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "admin/vehicle_form.html"
    success_url = reverse_lazy("waste_management:vehicle_list")

    def form_valid(self, form):
        messages.success(self.request, f"Vehicle '{form.instance.vehicle_number}' updated successfully.")
        return super().form_valid(form)


class VehicleStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        new_status = request.POST.get("status")
        if new_status in Vehicle.StatusChoices.values:
            vehicle.status = new_status
            vehicle.save(update_fields=["status"])
            messages.success(request, f"Vehicle '{vehicle.vehicle_number}' status updated to {new_status}.")
        return redirect("waste_management:vehicle_list")


class RouteListView(LoginRequiredMixin, ListView):
    model = Route
    template_name = "admin/route_list.html"
    context_object_name = "routes"
    queryset = Route.objects.select_related("vehicle", "hub", "hub__city", "vehicle__driver").prefetch_related("route_pickups").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_vehicles"] = Vehicle.objects.filter(status=Vehicle.StatusChoices.AVAILABLE)
        context["pending_pickups"] = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.PENDING).select_related("address", "city", "category")[:20]
        context["held_pickups"] = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.HELD).select_related("address", "city", "category")
        return context


class RouteDetailView(LoginRequiredMixin, DetailView):
    model = Route
    template_name = "admin/route_detail.html"
    context_object_name = "route"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route = self.object
        context["stops"] = route.get_ordered_stops()
        context["waypoints"] = route.get_waypoints()
        eligible_pickups = []
        from trashport.core.waste_management.services import RouteService
        if route.route_pickups.count() < route.vehicle.max_capacity:
            for p in PickupRequest.objects.filter(status__in=[PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.HELD]).select_related("address", "citizen", "category"):
                eval_res = RouteService.evaluate_route_suitability(route, p)
                if eval_res["suitable"]:
                    eligible_pickups.append({
                        "pickup": p,
                        "detour_km": eval_res["detour_km"],
                        "best_sequence": eval_res["best_sequence"],
                    })
        context["eligible_pickups"] = eligible_pickups
        return context


class RouteCreateView(LoginRequiredMixin, CreateView):
    model = Route
    form_class = RouteForm
    template_name = "admin/route_form.html"
    success_url = reverse_lazy("waste_management:route_list")

    def form_valid(self, form):
        form.instance.hub = form.instance.vehicle.hub
        messages.success(self.request, f"Route for vehicle '{form.instance.vehicle.vehicle_number}' created starting at {form.instance.hub.name}.")
        return super().form_valid(form)


class RouteAssignPickupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        route = get_object_or_404(Route, pk=pk)
        pickup_id = request.POST.get("pickup_id")
        from trashport.core.waste_management.services import RouteService
        from django.core.exceptions import ValidationError
        try:
            RouteService.assign_pickup_to_route(route.id, int(pickup_id))
            messages.success(request, f"Pickup #{pickup_id} successfully assigned to Route #{route.id}.")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, 'message') else str(e))
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("waste_management:route_detail", pk=pk)


class RouteHoldPickupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        reason = request.POST.get("reason", "Held by administrator")
        from trashport.core.waste_management.services import RouteService
        RouteService.hold_pickup_request(pickup.id, reason)
        messages.warning(request, f"Pickup #{pickup.display_id} placed on HELD.")
        next_url = request.POST.get("next") or reverse("waste_management:route_list")
        return redirect(next_url)



