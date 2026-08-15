"""
Collector-specific views for managing assigned collections, transit updates, and completions.
"""

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, TemplateView, View

from waste_management.models import PickupRequest


class CollectorDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Collector Dashboard.
    Displays:
    - Active assigned collections in progress.
    - Historical completed collections by this collector.
    - System-wide unassigned pending collections that can be claimed.
    """
    template_name = "collector/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role

        # Active assigned jobs
        context["assigned_pickups"] = PickupRequest.objects.filter(
            collector=user,
            status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]
        ).order_by("schedule_date")
        
        # History of completed jobs
        context["completed_pickups"] = PickupRequest.objects.filter(
            collector=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).order_by("-schedule_date")
        
        # Available jobs in system
        context["unassigned_pickups"] = PickupRequest.objects.filter(
            status=PickupRequest.StatusChoices.PENDING
        ).order_by("schedule_date")

        return context


class CollectorPickupRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a pickup request to a collector.
    """
    model = PickupRequest
    template_name = "collector/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        # Collectors are allowed to view details of any pickup in the system
        return PickupRequest.objects.all()


class CollectorPickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Handles POST requests from collectors updating the status of a pickup request.
    Supported actions:
    - claim: Assigns an unassigned pending request to the current collector.
    - transit: Marks the collection job as "In Transit".
    - complete: Collects actual weight, calculates cost, and marks request as "Completed".
    - cancel (release): Releases an assigned request back to "Pending" (releases collector).
    """
    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        action = request.POST.get("action")
        user = request.user

        if action == "claim":
            # Claiming a pending request
            pickup.collector = user
            pickup.status = PickupRequest.StatusChoices.ASSIGNED
            pickup.save()
            messages.success(request, "Pickup claimed successfully!")
        elif action == "transit" and pickup.collector == user:
            # Updating state to transit
            pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
            pickup.save()
            messages.success(request, "Status updated to In Transit.")
        elif action == "complete" and pickup.collector == user:
            # Completing the request (requires actual weight)
            weight_str = request.POST.get("weight")
            try:
                weight = Decimal(weight_str)
                if weight <= 0:
                    raise ValueError("Weight must be greater than zero.")
            except (TypeError, ValueError, InvalidOperation):
                messages.error(request, "Invalid weight value. Please enter a valid number greater than 0.")
                return redirect("waste_management:pickup_detail", pk=pk)

            pickup.weight = weight
            # Cost is based on weight * category price per kg
            pickup.cost = weight * pickup.category.price_per_kg
            pickup.status = PickupRequest.StatusChoices.COMPLETED
            pickup.payment_status = PickupRequest.PaymentStatus.UNPAID
            pickup.save()
            messages.success(request, f"Pickup completed successfully! Cost: ${pickup.cost:.2f}")
        elif action == "cancel" and pickup.collector == user:
            # Release job back to pending
            pickup.status = PickupRequest.StatusChoices.PENDING
            pickup.collector = None
            pickup.save()
            messages.warning(request, "Job released. Status reverted to Pending.")

        return redirect("waste_management:pickup_detail", pk=pk)
