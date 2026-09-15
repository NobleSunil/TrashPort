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
  - CSV export views directly stream to browser — changes affect downloaded files.
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
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from trashport.payments.models import UPIPayoutRequest
from trashport.users.models import User
from waste_management.models import (
    AnonymousFeedback,
    CollectorPayoutSetting,
    Complaint,
    PickupRequest,
    WasteCategory,
)
from .forms import (
    CollectorCreationForm,
    CollectorPayoutSettingForm,
    WalletPointAdjustmentForm,
    WasteCategoryForm,
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
            from trashport.payments.services import WalletService
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


