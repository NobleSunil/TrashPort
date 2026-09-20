"""
trashport/collectors/views.py — Collector Role View Layer
===========================================================

PURPOSE:
  This file contains all view classes exclusively used by collectors (waste
  collection staff). These are never called directly from URLs — they are
  dispatched to by the role-based system in waste_management/views.py.

HOW THESE VIEWS ARE REACHED:
  1. Collector visits /dashboard/ (registered in waste_management/urls.py)
  2. DashboardView (waste_management/views.py) sees user.role == COLLECTOR
  3. Delegates to CollectorDashboardView defined here

  Same pattern applies to: PickupRequestDetailView, PickupStatusUpdateView

CONNECTION MAP:
  - waste_management/views.py       → dispatches to CollectorDashboardView,
                                       CollectorPickupRequestDetailView,
                                       CollectorPickupStatusUpdateView
  - waste_management/models.py      → PickupRequest, CollectorPayoutSetting
  - trashport/collectors/models.py  → CollectorAadhaarProfile (for Aadhaar sync)
  - trashport/maps/models.py        → CollectorLocation (GPS position for map)
  - trashport/maps/services.py      → GeoService.haversine_distance() (distance calc)
  - trashport/payments/models.py    → UPIPayoutRequest (payout history)
  - waste_management/urls.py        → /wallet/redeem-upi/ → CollectorRedeemUPIView

COLLECTOR WORKFLOW:
  1. Collector opens dashboard → sees pending pickups sorted by distance
  2. Collector "claims" a pickup → PickupRequest.collector = user, status = ASSIGNED
  3. Collector drives to location → clicks "Mark In Transit" → status = IN_TRANSIT
  4. Collector arrives, weighs waste → submits actual weight → status = COMPLETED
     • If actual > estimated: extra_fee = excess × fee_per_kg × 2 (2x surcharge)
     • Collector earnings = base_min + (distance × rate_per_km) + (extra_fee × commission%)
     • Collector wallet_balance is credited immediately on COMPLETED
  5. Collector can release a claimed pickup → status = PENDING (no penalty)

AADHAAR VERIFICATION GATE:
  Collectors MUST be verified (user.is_verified = True) to claim or complete pickups.
  _sync_aadhaar_status() checks the CollectorAadhaarProfile and syncs the
  user.is_verified / user.verification_status fields if they are out of sync.

  If an Aadhaar profile exists and aadhaar_verified = True, but user.is_verified
  is still False (can happen if admin flag was reset), this auto-corrects it.

IMPACT:
  - Changing the claim logic in CollectorPickupStatusUpdateView.post() affects
    how collectors take on jobs.
  - Changing completion logic affects when wallet_balance is credited.
  - Changing _get_unassigned_pickup_data() affects which jobs appear on the map.
"""

import json
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, TemplateView, View

from trashport.core.maps.models import CollectorLocation
from trashport.core.maps.services import GeoService
from trashport.services.payments.models import UPIPayoutRequest
from trashport.users.models import User
from trashport.core.waste_management.models import CollectorPayoutSetting, PickupRequest


# ==============================================================================
# Collector Dashboard View
# ==============================================================================
# The main hub for collectors. Shows:
#   - Verification status (Aadhaar must be verified to claim jobs)
#   - Cash wallet balance (credited on pickup completion)
#   - Assigned/In-Transit active jobs
#   - Completed jobs with earnings breakdown
#   - System-wide unassigned jobs sorted nearest-first on a Leaflet map
#   - UPI payout history and redeem controls
#
# CONNECTION: Dispatched from DashboardView in waste_management/views.py.
#             Template: templates/collector/dashboard.html
# ==============================================================================

class CollectorDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Collector Dashboard.

    Context variables provided to the template:
      role                  : User.Roles.COLLECTOR (string)
      is_verified           : bool — whether collector passed Aadhaar verification
      verification_status   : "PENDING" / "APPROVED" / "REJECTED" string for badge display
      wallet_balance        : Decimal — current cash balance available for UPI withdrawal
      assigned_pickups      : QuerySet of ASSIGNED and IN_TRANSIT pickups
      completed_pickups     : QuerySet of COMPLETED pickups (newest first)
      completed_count       : int — count of all completed jobs (for stats display)
      total_earned          : Decimal — sum of collector_earnings across all completed jobs
      unassigned_pickups    : List of PENDING PickupRequest objects sorted nearest-first
                              (each enriched with .calculated_distance_km and .calculated_earnings)
      collector_lat/lng     : float — collector's GPS position (from CollectorLocation or Kerala default)
      unassigned_pickups_json: JSON string for Leaflet map pin rendering
      upi_payouts           : Last 10 UPIPayoutRequest records for this collector
      total_redeemed_upi    : Decimal — total UPI redemptions so far
      aadhaar_verified      : bool — True if Aadhaar verification passed
      aadhaar_masked        : str  — "XXXX-XXXX-1234" display string
      payout_settings       : CollectorPayoutSetting — base/km/commission rates for display
    """
    template_name = "collector/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- Basic collector profile data ---
        context["role"] = user.role
        context["is_verified"] = getattr(user, "is_verified", False)
        context["verification_status"] = getattr(user, "verification_status", "PENDING")
        context["wallet_balance"] = getattr(user, "wallet_balance", Decimal("0.00"))

        # --- Active jobs currently assigned or in transit ---
        # ASSIGNED = collector claimed it but hasn't started driving yet
        # IN_TRANSIT = collector is en route to pickup location
        context["assigned_pickups"] = PickupRequest.objects.filter(
            collector=user,
            status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]
        ).select_related("citizen", "address", "category").order_by("schedule_date")

        # --- Completed jobs history and earnings summary ---
        completed_qs = PickupRequest.objects.filter(
            collector=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).select_related("citizen", "address", "category").order_by("-schedule_date")
        context["completed_pickups"] = completed_qs
        context["completed_count"] = completed_qs.count()

        # Total lifetime earnings from completed pickups
        total_earned = completed_qs.aggregate(total=Sum("collector_earnings"))["total"] or Decimal("0.00")
        context["total_earned"] = total_earned

        # --- Available jobs on the map (sorted nearest-first) ---
        # See _get_unassigned_pickup_data() below for full explanation
        unassigned_list, col_lat, col_lng, pickups_json = self._get_unassigned_pickup_data(user)
        context["unassigned_pickups"] = unassigned_list
        context["collector_lat"] = col_lat
        context["collector_lng"] = col_lng
        context["unassigned_pickups_json"] = pickups_json

        # --- UPI payout/withdrawal history ---
        context["upi_payouts"] = UPIPayoutRequest.objects.filter(collector=user).order_by("-created_at")[:10]
        context["total_redeemed_upi"] = (
            UPIPayoutRequest.objects.filter(collector=user, status=UPIPayoutRequest.Statuses.COMPLETED)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        # --- Aadhaar verification status ---
        # Syncs user.is_verified with the Aadhaar pro        # --- Payout formula settings (for display in dashboard sidebar) ---
        context["payout_settings"] = CollectorPayoutSetting.get_settings()

        # --- Hub registration context & Map Display ---
        from trashport.core.waste_management.models import Hub
        available_hubs_qs = Hub.objects.filter(is_active=True).select_related("city").order_by("city__name", "name")
        context["collector_hub"] = user.hub
        context["available_hubs"] = available_hubs_qs
        hubs_list = [
            {
                "id": h.id,
                "name": h.name,
                "city": h.city.name,
                "latitude": float(h.latitude),
                "longitude": float(h.longitude),
                "address": h.address,
                "is_current": bool(user.hub and user.hub.id == h.id),
            }
            for h in available_hubs_qs
        ]
        context["hubs_json"] = json.dumps(hubs_list)
        return context

    def post(self, request, *args, **kwargs):
        """Allows collectors to register or switch their assigned Hub."""
        hub_id = request.POST.get("hub_id")
        if hub_id:
            from trashport.core.waste_management.models import Hub
            hub = get_object_or_404(Hub, pk=hub_id, is_active=True)
            request.user.hub = hub
            messages.success(request, f"Successfully registered to {hub.name} ({hub.city.name}).")
        return redirect("waste_management:dashboard")

    def _get_unassigned_pickup_data(self, user):
        """
        Fetches all unassigned PENDING pickups, calculates distance from the
        collector's live GPS position (or hub anchor / default), and returns data
        strictly filtered within the 25 km collector operating range.
        Dynamically aligns user.hub to the nearest active Hub within 25 km.
        """
        # --- 1. Determine reference position: live GPS takes precedence ---
        col_location = CollectorLocation.objects.filter(collector=user).first()
        if col_location:
            col_lat = float(col_location.latitude)
            col_lng = float(col_location.longitude)
            # Auto-align hub to nearest hub based on live location if within 25 km
            from trashport.core.waste_management.models import Hub
            hubs = list(Hub.objects.filter(is_active=True))
            if hubs:
                nearest_hub = min(
                    hubs,
                    key=lambda h: GeoService.haversine_distance(col_lat, col_lng, float(h.latitude), float(h.longitude))
                )
                nearest_dist = GeoService.haversine_distance(col_lat, col_lng, float(nearest_hub.latitude), float(nearest_hub.longitude))
                if nearest_dist <= 25.0 and user.hub != nearest_hub:
                    user.hub = nearest_hub
                    user.save()
        elif user.hub:
            col_lat = float(user.hub.latitude)
            col_lng = float(user.hub.longitude)
        else:
            col_lat = 9.9312
            col_lng = 76.2673

        # --- 2. Fetch all unassigned pickups (PENDING or AWAITING_PAYMENT without a collector) ---
        unassigned_qs = PickupRequest.objects.filter(
            status__in=[PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT],
            collector__isnull=True
        ).select_related("citizen", "address", "category")

        # --- 3. Annotate each pickup with distance and earnings preview ---
        unassigned_list = list(unassigned_qs)
        for p in unassigned_list:
            plat = float(p.effective_latitude)
            plng = float(p.effective_longitude)
            # Straight-line (haversine) distance from collector's live location to pickup location
            p.calculated_distance_km = GeoService.haversine_distance(col_lat, col_lng, plat, plng)
            p.calculated_earnings = p.calculate_collector_earnings()

        # --- 4. Strict 25 km service range limit for all collectors ---
        MAX_COLLECTOR_RANGE_KM = 25.0
        unassigned_list = [p for p in unassigned_list if p.calculated_distance_km <= MAX_COLLECTOR_RANGE_KM]

        # --- Sort nearest first, cap at 50 ---
        unassigned_list.sort(key=lambda item: item.calculated_distance_km)
        unassigned_list = unassigned_list[:50]

        # --- Build Leaflet JSON pin data ---
        pickups_json_data = []
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
        """
        Syncs the collector's User.is_verified and User.verification_status
        flags with their CollectorAadhaarProfile record.

        WHY THIS EXISTS:
          The User model has is_verified and verification_status fields that
          are managed by admins. However, after a collector completes Aadhaar
          OTP verification (via aadhaar_views.py), only the CollectorAadhaarProfile
          is updated. If the admin later resets the User flag, this method
          auto-corrects it back to APPROVED when the collector's Aadhaar is confirmed.

        IMPACT:
          - Modifies user.is_verified and user.verification_status in DB if they
            are out of sync with the Aadhaar profile.
          - If CollectorAadhaarProfile doesn't exist (Aadhaar not submitted yet),
            context gets aadhaar_verified = False.

        CONNECTION: CollectorAadhaarProfile is in trashport/collectors/models.py.
        """
        from trashport.collectors.models import CollectorAadhaarProfile
        try:
            aadhaar_profile = CollectorAadhaarProfile.objects.get(collector=user)
            context["aadhaar_verified"] = aadhaar_profile.aadhaar_verified
            context["aadhaar_masked"] = aadhaar_profile.aadhaar_masked or ""
            if aadhaar_profile.aadhaar_verified:
                context["is_verified"] = True
                context["verification_status"] = "APPROVED"
                # Auto-correct: if Aadhaar is verified but User flags are stale, fix them
                if not user.is_verified:
                    user.is_verified = True
                    user.verification_status = "APPROVED"
                    user.save(update_fields=["is_verified", "verification_status"])
        except CollectorAadhaarProfile.DoesNotExist:
            # Collector hasn't submitted Aadhaar yet
            context["aadhaar_verified"] = False
            context["aadhaar_masked"] = ""


# ==============================================================================
# Collector Pickup Detail View
# ==============================================================================
# Shows a collector the full detail of a single pickup request.
# Includes interactive weight verification form and earnings preview.
#
# CONNECTION: Dispatched from PickupRequestDetailView in waste_management/views.py.
#             Template: templates/collector/pickup_detail.html
# ==============================================================================

class CollectorPickupRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a pickup request to a collector, including
    the interactive waste weight verification form and earning preview.

    Access: Any authenticated collector can view ANY pickup (not filtered by
    collector=user), since a collector may need to view details of unassigned
    pickups they're considering claiming.

    Context additions:
      is_verified     : bool — guard for claim/complete action buttons in template
      preview_earnings: Decimal — estimated earnings based on current payout settings
      payout_settings : CollectorPayoutSetting — rates displayed in earnings breakdown
    """
    model = PickupRequest
    template_name = "collector/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        # Collectors can view ALL pickup details (not just their own)
        # so they can inspect pickups they haven't claimed yet
        return PickupRequest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        pickup = self.object

        # Determine collector's reference location
        col_location = CollectorLocation.objects.filter(collector=user).first()
        if col_location:
            col_lat, col_lng = float(col_location.latitude), float(col_location.longitude)
        elif user.hub:
            col_lat, col_lng = float(user.hub.latitude), float(user.hub.longitude)
        else:
            col_lat, col_lng = 9.9312, 76.2673

        plat = float(pickup.effective_latitude)
        plng = float(pickup.effective_longitude)
        dist_km = GeoService.haversine_distance(col_lat, col_lng, plat, plng)

        context["distance_from_collector_km"] = dist_km
        context["is_within_collector_range"] = (dist_km <= 25.0)

        # Gate flag: if not verified, template hides claim/complete action buttons
        context["is_verified"] = getattr(user, "is_verified", False)
        # Preview how much the collector would earn if they claim and complete this job
        context["preview_earnings"] = pickup.calculate_collector_earnings()
        # Show payout formula rates (base, per km, commission %) for transparency
        context["payout_settings"] = CollectorPayoutSetting.get_settings()
        return context


# ==============================================================================
# Collector Pickup Status Update View
# ==============================================================================
# Handles all collector status actions via POST:
#   - claim   : collector takes ownership of a PENDING pickup (guarded by 25 km limit)
#   - transit : collector is now driving to the pickup location
#   - complete: collector submits measured weight; completes job; credits wallet
#   - cancel  : collector releases the pickup back to PENDING
#
# VERIFICATION GATE: All actions require user.is_verified = True.
# Unverified collectors are shown an error and blocked from any action.
#
# CONNECTION: Dispatched from PickupStatusUpdateView in waste_management/views.py.
#             PickupRequest.save() does the earnings calculation and wallet credit
#             automatically when status → COMPLETED.
# ==============================================================================

class CollectorPickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Handles POST requests for collector-initiated pickup status changes.

    Verification Gate:
      If user.is_verified is False, ALL actions are blocked with an error message.
      This gate is checked before any action processing.

    Action: "claim"
      - Validates pickup is PENDING or AWAITING_PAYMENT (not already taken).
      - Enforces 25 km collection range from collector's live location / hub.
      - Sets pickup.collector = current user and pickup.status = ASSIGNED.
      - pickup.save() triggers the assignment notification (see models.py).

    Action: "transit"
      - Validates this collector owns the pickup.
      - Sets status = IN_TRANSIT.

    Action: "complete"
      - Validates this collector owns the pickup.
      - Reads actual_weight_kg from POST form input.
      - Sets pickup.actual_weight_kg, is_weight_verified = True, status = COMPLETED.
      - pickup.save() AUTOMATICALLY:
          • Calculates extra_fee for excess weight (2x rate)
          • Recalculates collector_earnings
          • Credits citizen wallet_points
          • Credits collector wallet_balance
        (All of this happens inside PickupRequest.save() —  see models.py)

    Action: "cancel" (release)
      - Validates this collector owns the pickup.
      - Sets pickup.collector = None and status = PENDING.
      - No penalty for releasing —  pickup returns to the available pool.
    """

    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        action = request.POST.get("action")
        user = request.user

        # ---- VERIFICATION GATE: Block all actions for unverified collectors ----
        # This prevents unverified collectors from handling real waste jobs
        if not getattr(user, "is_verified", False):
            messages.error(
                request,
                "Your collector account is pending administrator verification. "
                "You cannot claim or execute pickups until approved."
            )
            return redirect("waste_management:pickup_detail", pk=pk)

        # ---- ACTION: claim ----
        if action == "claim":
            # Double-check status hasn't changed since page load (race condition guard)
            if pickup.status not in [PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT]:
                messages.error(request, "This pickup request is no longer available to claim.")
            else:
                # 25 km collection range guard
                col_location = CollectorLocation.objects.filter(collector=user).first()
                if col_location:
                    col_lat, col_lng = float(col_location.latitude), float(col_location.longitude)
                elif user.hub:
                    col_lat, col_lng = float(user.hub.latitude), float(user.hub.longitude)
                else:
                    col_lat, col_lng = 9.9312, 76.2673

                plat = float(pickup.effective_latitude)
                plng = float(pickup.effective_longitude)
                dist_km = GeoService.haversine_distance(col_lat, col_lng, plat, plng)

                if dist_km > 25.0:
                    messages.error(
                        request,
                        f"Cannot claim pickup: this location is {dist_km:.1f} km away, which exceeds your maximum 25 km collection range."
                    )
                    return redirect("waste_management:pickup_detail", pk=pk)

                pickup.collector = user
                pickup.status = PickupRequest.StatusChoices.ASSIGNED
                # save() triggers send_pickup_assigned_notification() in models.py
                pickup.save()
                messages.success(request, "Pickup job claimed successfully! You can claim multiple jobs to optimize your collection route.")
                return redirect(reverse("waste_management:pickup_detail", kwargs={"pk": pk}) + "?just_claimed=true")

        # ---- ACTION: transit (mark en route) ----
        elif action == "transit" and pickup.collector == user:
            pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
            pickup.save()
            messages.success(request, "Status updated to In Transit.")

        # ---- ACTION: complete (submit actual weight and close the job) ----
        elif action == "complete" and pickup.collector == user:
            actual_weight_input = request.POST.get("actual_weight_kg", "").strip()

            if actual_weight_input:
                try:
                    actual_wt = Decimal(actual_weight_input)
                    if actual_wt <= 0:
                        messages.error(request, "Measured weight must be greater than 0 kg.")
                        return redirect("waste_management:pickup_detail", pk=pk)
                    # Set the actual measured weight (triggers extra_fee calc in save())
                    pickup.actual_weight_kg = actual_wt
                    pickup.is_weight_verified = True
                except Exception:
                    messages.error(request, "Invalid weight format entered.")
                    return redirect("waste_management:pickup_detail", pk=pk)
            else:
                # No weight input: accept citizen's estimate as verified actual weight
                pickup.actual_weight_kg = pickup.weight_kg
                pickup.is_weight_verified = True

            pickup.status = PickupRequest.StatusChoices.COMPLETED
            # save() handles: extra_fee, earnings recalc, wallet credits, notifications
            pickup.save()

            # Build a detailed completion success message for the collector
            msg = (
                f"Pickup #{pickup.id} verified & completed! "
                f"Measured: {pickup.actual_weight_kg}kg. "
            )
            if pickup.extra_fee > Decimal("0.00"):
                msg += f"Extra Weight Charge (2x): +Rs. {pickup.extra_fee:.2f}. "
            msg += (
                f"Earnings: Rs. {pickup.collector_earnings:.2f} "
                f"(Rs 25 min + Rs 2/km + 20% extra wt commission) credited to your Wallet."
            )
            messages.success(request, msg)

        # ---- ACTION: cancel / release ----
        elif action == "cancel" and pickup.collector == user:
            # Collector changes their mind — release back to available pool
            pickup.status = PickupRequest.StatusChoices.PENDING
            pickup.collector = None
            pickup.save()
            messages.warning(request, "Job released. Status reverted to Pending.")

        return redirect("waste_management:pickup_detail", pk=pk)


# ==============================================================================
# Collector UPI Wallet Redemption View
# ==============================================================================
# Allows verified collectors to withdraw their wallet_balance (cash earned
# from completed pickups) to a UPI address.
#
# URL: /wallet/redeem-upi/  (POST only)
# Dispatcher: CollectorRedeemUPIView in waste_management/views.py → this class
#
# PROCESS:
#   1. Validate collector is verified (is_verified = True)
#   2. Validate UPI ID is provided
#   3. Validate amount is positive and does not exceed wallet_balance
#   4. Deduct amount from user.wallet_balance
#   5. Create UPIPayoutRequest record (auditable payout ledger)
#   6. Show success message with transaction reference
#
# CONNECTION:
#   - trashport/payments/models.py → UPIPayoutRequest (payout audit log)
#   - trashport/users/models.py    → User.wallet_balance (cash balance field)
# ==============================================================================

class CollectorRedeemUPIView(LoginRequiredMixin, View):
    """
    Handles POST: collector withdraws wallet cash balance to a UPI address.

    Guards:
      1. user.role == COLLECTOR (role check)
      2. user.is_verified == True (verification gate)
      3. Amount > 0 and <= user.wallet_balance (balance check)

    On success:
      - Deducts amount from user.wallet_balance (saved to DB)
      - Creates a UPIPayoutRequest record with COMPLETED status
      - Displays success message with unique transaction reference ID
    """

    def post(self, request, *args, **kwargs):
        user = request.user

        # ---- Guard: only collectors can redeem wallet ----
        if user.role != User.Roles.COLLECTOR:
            messages.error(request, "Only collectors can redeem wallet balance.")
            return redirect("waste_management:dashboard")

        # ---- Guard: must be verified to withdraw ----
        if not getattr(user, "is_verified", False):
            messages.error(request, "Your account must be verified by an admin before you can redeem to UPI.")
            return redirect("waste_management:dashboard")

        # ---- Input validation ----
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

        # ---- Balance check ----
        current_balance = Decimal(str(user.wallet_balance or "0.00"))
        if amount > current_balance:
            messages.error(request, f"Insufficient balance. Current available wallet balance is Rs. {current_balance:.2f}.")
            return redirect("waste_management:dashboard")

        # ---- Deduct wallet balance ----
        user.wallet_balance = current_balance - amount
        user.save()

        # ---- Create payout audit record ----
        ref_id = f"UPI-{uuid.uuid4().hex[:8].upper()}"  # e.g., "UPI-A3F9C12B"
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
            f"🎉 Success! Rs. {amount:.2f} has been redeemed to UPI ID '{upi_id}'. "
            f"Transaction Reference: {ref_id}."
        )
        return redirect("waste_management:dashboard")
