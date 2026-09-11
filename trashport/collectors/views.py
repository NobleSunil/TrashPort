"""
Collector-specific views for managing assigned collections, transit updates,
waste weight verification (with 2x extra charge for excess weight),
earnings calculation (35% fee + Rs 0.25/km), and UPI wallet redemption.
"""

import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, TemplateView, View

from trashport.payments.models import UPIPayoutRequest
from trashport.users.models import User
from waste_management.models import PickupRequest


class CollectorDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Collector Dashboard.
    Displays:
    - Collector Verification Status (Pending / Verified / Rejected)
    - Collector Cash Wallet Balance & Total Earnings
    - UPI Redemption controls and Payout History
    - Active assigned collections in progress.
    - Historical completed collections with fee, distance, and payout breakdown.
    - System-wide unassigned pending collections that can be claimed.
    """
    template_name = "collector/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role
        context["is_verified"] = getattr(user, "is_verified", False)
        context["verification_status"] = getattr(user, "verification_status", "PENDING")
        context["wallet_balance"] = getattr(user, "wallet_balance", Decimal("0.00"))

        # Active assigned jobs
        context["assigned_pickups"] = PickupRequest.objects.filter(
            collector=user,
            status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]
        ).select_related("citizen", "address", "category").order_by("schedule_date")
        
        # History of completed jobs
        completed_qs = PickupRequest.objects.filter(
            collector=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).select_related("citizen", "address", "category").order_by("-schedule_date")
        context["completed_pickups"] = completed_qs
        context["completed_count"] = completed_qs.count()

        total_earned = completed_qs.aggregate(total=Sum("collector_earnings"))["total"] or Decimal("0.00")
        context["total_earned"] = total_earned

        # Available jobs in system (with proximity calculation & nearest-first sorting)
        unassigned_list, col_lat, col_lng, pickups_json = self._get_unassigned_pickup_data(user)
        context["unassigned_pickups"] = unassigned_list
        context["collector_lat"] = col_lat
        context["collector_lng"] = col_lng
        context["unassigned_pickups_json"] = pickups_json

        # UPI Payout / Redemption history
        context["upi_payouts"] = UPIPayoutRequest.objects.filter(collector=user).order_by("-created_at")[:10]
        context["total_redeemed_upi"] = (
            UPIPayoutRequest.objects.filter(collector=user, status=UPIPayoutRequest.Statuses.COMPLETED)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        # Aadhaar verification status sync
        self._sync_aadhaar_status(user, context)
        from waste_management.models import CollectorPayoutSetting
        context["payout_settings"] = CollectorPayoutSetting.get_settings()
        return context

    def _get_unassigned_pickup_data(self, user):
        """Helper to fetch, calculate distance, and format unassigned pickups as JSON for Leaflet maps."""
        import json
        from trashport.maps.models import CollectorLocation
        from trashport.maps.services import GeoService

        col_location = CollectorLocation.objects.filter(collector=user).first()
        # Default Kerala coordinates (Kochi/Central Kerala: 9.9312, 76.2673)
        col_lat = float(col_location.latitude) if col_location else 9.9312
        col_lng = float(col_location.longitude) if col_location else 76.2673

        unassigned_qs = PickupRequest.objects.filter(
            status__in=[PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT],
            collector__isnull=True
        ).select_related("citizen", "address", "category")

        unassigned_list = list(unassigned_qs)
        pickups_json_data = []
        for p in unassigned_list:
            plat = float(p.effective_latitude)
            plng = float(p.effective_longitude)
            dist = GeoService.haversine_distance(col_lat, col_lng, plat, plng)
            p.calculated_distance_km = dist
            p.calculated_earnings = p.calculate_collector_earnings()

        unassigned_list.sort(key=lambda item: item.calculated_distance_km)
        unassigned_list = unassigned_list[:50]

        for p in unassigned_list:
            pickups_json_data.append({
                "id": p.id,
                "category": p.category.name if p.category else "Waste",
                "citizen_name": p.citizen.name or p.citizen.email,
                "address": f"{p.address.address_line1}, {p.address.city}" if p.address else "",
                "latitude": float(p.effective_latitude),
                "longitude": float(p.effective_longitude),
                "distance_km": float(p.calculated_distance_km),
                "earnings": float(p.calculated_earnings),
                "weight_kg": float(p.weight_kg),
                "schedule_date": p.schedule_date.strftime("%b %d, %Y") if p.schedule_date else "",
            })
        return unassigned_list, col_lat, col_lng, json.dumps(pickups_json_data)

    def _sync_aadhaar_status(self, user, context):
        """Helper to sync CollectorAadhaarProfile state with User verification status."""
        from trashport.collectors.models import CollectorAadhaarProfile
        try:
            aadhaar_profile = CollectorAadhaarProfile.objects.get(collector=user)
            context["aadhaar_verified"] = aadhaar_profile.aadhaar_verified
            context["aadhaar_masked"] = aadhaar_profile.aadhaar_masked or ""
            if aadhaar_profile.aadhaar_verified:
                context["is_verified"] = True
                context["verification_status"] = "APPROVED"
                if not user.is_verified:
                    user.is_verified = True
                    user.save(update_fields=["verification_status"])
        except CollectorAadhaarProfile.DoesNotExist:
            context["aadhaar_verified"] = False
            context["aadhaar_masked"] = ""


class CollectorPickupRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a pickup request to a collector,
    including the interactive waste weight verification and earning preview.
    """
    model = PickupRequest
    template_name = "collector/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        return PickupRequest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pickup = self.object
        context["is_verified"] = getattr(user, "is_verified", False)
        context["preview_earnings"] = pickup.calculate_collector_earnings()
        from waste_management.models import CollectorPayoutSetting
        context["payout_settings"] = CollectorPayoutSetting.get_settings()
        return context


class CollectorPickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Handles POST requests from collectors updating the status of a pickup request.
    Enforces verification check: unverified collectors cannot claim jobs.
    Supported actions:
    - claim: Assigns an unassigned pending request to the current collector.
    - transit: Marks the collection job as "In Transit".
    - complete: Measures actual waste weight, calculates extra weight penalty (2x rate),
                recalculates Rs 25 min + Rs 2/km + 20% extra weight commission, and credits collector wallet.
    - cancel (release): Releases an assigned request back to "Pending".
    """
    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        action = request.POST.get("action")
        user = request.user

        if not getattr(user, "is_verified", False):
            messages.error(
                request,
                "Your collector account is pending administrator verification. You cannot claim or execute pickups until approved."
            )
            return redirect("waste_management:pickup_detail", pk=pk)

        if action == "claim":
            if pickup.status not in [PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT]:
                messages.error(request, "This pickup request is no longer available to claim.")
            else:
                pickup.collector = user
                pickup.status = PickupRequest.StatusChoices.ASSIGNED
                pickup.save()
                messages.success(request, "Pickup job claimed successfully! You can claim multiple jobs to optimize your collection route.")
                return redirect(reverse("waste_management:pickup_detail", kwargs={"pk": pk}) + "?just_claimed=true")
        elif action == "transit" and pickup.collector == user:
            pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
            pickup.save()
            messages.success(request, "Status updated to In Transit.")
        elif action == "complete" and pickup.collector == user:
            actual_weight_input = request.POST.get("actual_weight_kg", "").strip()
            if actual_weight_input:
                try:
                    actual_wt = Decimal(actual_weight_input)
                    if actual_wt <= 0:
                        messages.error(request, "Measured weight must be greater than 0 kg.")
                        return redirect("waste_management:pickup_detail", pk=pk)
                    pickup.actual_weight_kg = actual_wt
                    pickup.is_weight_verified = True
                except Exception:
                    messages.error(request, "Invalid weight format entered.")
                    return redirect("waste_management:pickup_detail", pk=pk)
            else:
                pickup.actual_weight_kg = pickup.weight_kg
                pickup.is_weight_verified = True

            pickup.status = PickupRequest.StatusChoices.COMPLETED
            pickup.save()

            msg = (
                f"Pickup #{pickup.id} verified & completed! "
                f"Measured: {pickup.actual_weight_kg}kg. "
            )
            if pickup.extra_fee > Decimal("0.00"):
                msg += f"Extra Weight Charge (2x): +Rs. {pickup.extra_fee:.2f}. "
            msg += f"Earnings: Rs. {pickup.collector_earnings:.2f} (Rs 25 min + Rs 2/km + 20% extra wt commission) credited to your Wallet."
            messages.success(request, msg)

        elif action == "cancel" and pickup.collector == user:
            pickup.status = PickupRequest.StatusChoices.PENDING
            pickup.collector = None
            pickup.save()
            messages.warning(request, "Job released. Status reverted to Pending.")

        return redirect("waste_management:pickup_detail", pk=pk)


class CollectorRedeemUPIView(LoginRequiredMixin, View):
    """
    Handles POST requests from collectors to redeem/withdraw wallet cash balance directly to UPI.
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role != User.Roles.COLLECTOR:
            messages.error(request, "Only collectors can redeem wallet balance.")
            return redirect("waste_management:dashboard")

        if not getattr(user, "is_verified", False):
            messages.error(request, "Your account must be verified by an admin before you can redeem to UPI.")
            return redirect("waste_management:dashboard")

        upi_id = request.POST.get("upi_id", "").strip()
        amount_raw = request.POST.get("amount", "").strip()

        if not upi_id:
            messages.error(request, "Please provide a valid UPI ID (e.g. yourname@okhdfcbank).")
            return redirect("waste_management:dashboard")

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal("0.00"):
                messages.error(request, "Withdrawal amount must be greater than Rs. 0.")
                return redirect("waste_management:dashboard")
        except Exception:
            messages.error(request, "Invalid withdrawal amount entered.")
            return redirect("waste_management:dashboard")

        current_balance = Decimal(str(user.wallet_balance or "0.00"))
        if amount > current_balance:
            messages.error(request, f"Insufficient balance. Current available wallet balance is Rs. {current_balance:.2f}.")
            return redirect("waste_management:dashboard")

        # Deduct wallet balance
        user.wallet_balance = current_balance - amount
        user.save()

        # Create UPI payout record
        ref_id = f"UPI-{uuid.uuid4().hex[:8].upper()}"
        UPIPayoutRequest.objects.create(
            collector=user,
            amount=amount,
            upi_id=upi_id,
            transaction_ref=ref_id,
            status=UPIPayoutRequest.Statuses.COMPLETED,
            note=f"Redeemed Rs. {amount} to UPI: {upi_id}",
        )

        messages.success(
            request,
            f"🎉 Success! Rs. {amount:.2f} has been redeemed to UPI ID '{upi_id}'. Transaction Reference: {ref_id}."
        )
        return redirect("waste_management:dashboard")
