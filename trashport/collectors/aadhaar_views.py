"""
trashport/collectors/aadhaar_views.py — Aadhaar OTP Verification API Endpoints
================================================================================

PURPOSE:
  JSON API views that implement the two-step simulated Aadhaar OTP verification
  flow for collector onboarding. Scoped exclusively to Collector users.

CONNECTION MAP:
  - trashport/collectors/urls.py     → registers the two endpoints:
      POST /api/collectors/aadhaar/initiate/ → AadhaarInitiateView
      POST /api/collectors/aadhaar/verify/   → AadhaarVerifyView
  - trashport/collectors/aadhaar_service.py → all validation, OTP, and hash logic
  - trashport/collectors/models.py   → CollectorAadhaarProfile (stores hash + status)
  - trashport/collectors/views.py    → _sync_aadhaar_status() reads the profile
                                        and syncs user.is_verified on dashboard load

TWO-STEP FLOW:
  Step 1 — AadhaarInitiateView (POST /aadhaar/initiate/):
    1. Verify user is a COLLECTOR (role check)
    2. Validate Aadhaar format + Verhoeff checksum
    3. Generate 6-digit OTP → store in Django cache for 5 minutes
    4. In DEMO mode: log OTP to server console (INFO level)
    5. Return JSON {"success": true, "uid": <hash-based session ID>}

  Step 2 — AadhaarVerifyView (POST /aadhaar/verify/):
    1. Read UID + OTP from request
    2. Validate OTP against Django cache entry
    3. On success:
       a. Create or update CollectorAadhaarProfile (aadhaar_verified = True)
       b. Store hash_aadhaar(number) and mask_aadhaar(number) in profile
       c. Set user.is_verified = True, user.verification_status = "APPROVED"
    4. Return JSON {"success": true} or {"success": false, "error": ...}

SCOPE GUARD:
  Both endpoints check user.role == COLLECTOR. Admins and citizens cannot
  initiate Aadhaar verification (returns HTTP 403 Forbidden JSON).

DEMO / ACADEMIC PROJECT NOTE:
  AADHAAR_MODE = demo
  This implementation is a simulated flow for a college/university project.
  It does NOT connect to UIDAI or any live government authentication service.
  Doing so without an AUA/KUA license (Aadhaar Act 2016, Section 4) is illegal.
  OTPs are logged to the Django logger at INFO level as:
      [DEMO MODE - OTP: xxxxxx]

FIELD SECURITY NOTE:
  - aadhaar_hash   : SHA-256 hash of the raw Aadhaar number (NEVER stored as plaintext)
  - aadhaar_masked : Display string like "XXXX-XXXX-1234" (last 4 digits only)
  - Raw 12-digit Aadhaar number is ONLY held in memory during verification,
    then immediately discarded.

IMPACT:
  - To connect to real Aadhaar API: replace OTP generation in
    AadhaarInitiateView with licensed provider SDK call.
  - To change OTP expiry: modify the cache TTL in aadhaar_service.store_otp_in_cache().
  - Role guard logic is in each view — if new roles need Aadhaar, update both views.
"""

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

from .aadhaar_service import (
    verhoeff_validate,
    generate_demo_otp,
    send_aadhaar_otp_email,
    sha256_hash,
    mask_aadhaar,
)
from .models import CollectorAadhaarProfile

logger = logging.getLogger(__name__)

# OTP validity window in minutes
OTP_EXPIRY_MINUTES = 5

# Maximum OTP verification attempts before locking
MAX_OTP_ATTEMPTS = 3


class AadhaarVerifyPageView(LoginRequiredMixin, TemplateView):
    """
    GET /api/collectors/aadhaar/

    Renders the Aadhaar verification HTML page.
    Scoped to Collector users — redirects others to dashboard.
    If already verified, redirects straight to dashboard.
    """
    template_name = "collector/aadhaar_verify.html"

    def dispatch(self, request, *args, **kwargs):
        """Redirect non-collectors and already-verified collectors."""
        from trashport.users.models import User
        if request.user.is_authenticated:
            if request.user.role != User.Roles.COLLECTOR:
                return redirect("/dashboard/")
            # If already verified, skip straight to dashboard
            try:
                profile = CollectorAadhaarProfile.objects.get(collector=request.user)
                if profile.aadhaar_verified:
                    return redirect("/dashboard/")
            except CollectorAadhaarProfile.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
class AadhaarInitiateView(View):
    """
    POST /api/collectors/aadhaar/initiate/

    Accepts a 12-digit Aadhaar number, validates its format and Verhoeff
    checksum, generates a simulated 6-digit OTP, and returns a reference ID
    for the subsequent verify call.

    Request body (JSON):
        { "aadhaar_number": "304332181964" }

    Responses:
        200 OK:
            {
                "reference_id": "<uuid>",
                "masked_aadhaar": "XXXX XXXX 1964",
                "expires_in": 300,
                "demo_mode": true
            }
        400 Bad Request:
            { "error": "<reason>" }
        403 Forbidden:
            { "error": "Only Collector accounts can use Aadhaar verification." }
    """

    # -------------------------------------------------------------------------
    # Scope guard — only collectors may use this endpoint
    # -------------------------------------------------------------------------
    def _check_collector(self, user):
        from trashport.users.models import User
        if user.role != User.Roles.COLLECTOR:
            return JsonResponse(
                {"error": "Only Collector accounts can use Aadhaar verification."},
                status=403,
            )
        return None

    def post(self, request, *args, **kwargs):
        # --- Scope guard -------------------------------------------------
        scope_err = self._check_collector(request.user)
        if scope_err:
            return scope_err

        # --- Parse body --------------------------------------------------
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        aadhaar_number = str(data.get("aadhaar_number", "")).strip()
        linked_email = str(data.get("linked_email", "") or getattr(request.user, "email", "")).strip()

        # --- Email validation --------------------------------------------
        if not linked_email:
            return JsonResponse(
                {"error": "Please enter the email address linked to your Aadhaar."},
                status=400,
            )
        # Basic email format check
        import re as _re
        if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', linked_email):
            return JsonResponse(
                {"error": "Please enter a valid email address."},
                status=400,
            )

        # --- Format validation -------------------------------------------
        if not aadhaar_number:
            return JsonResponse({"error": "aadhaar_number is required."}, status=400)

        if not aadhaar_number.isdigit() or len(aadhaar_number) != 12:
            return JsonResponse(
                {"error": "Aadhaar number must be exactly 12 numeric digits."},
                status=400,
            )

        # --- Verhoeff checksum validation --------------------------------
        if not verhoeff_validate(aadhaar_number):
            return JsonResponse(
                {
                    "error": (
                        "Invalid Aadhaar number (checksum failed). "
                        "Please enter a valid 12-digit Aadhaar number. "
                        "Use one of the provided demo numbers for testing."
                    )
                },
                status=400,
            )

        # --- Compute hash & mask (never store raw number) ----------------
        aadhaar_h = sha256_hash(aadhaar_number)
        aadhaar_masked = mask_aadhaar(aadhaar_number)

        # --- Check if already verified -----------------------------------
        profile, _ = CollectorAadhaarProfile.objects.get_or_create(
            collector=request.user
        )

        if profile.aadhaar_verified:
            return JsonResponse(
                {
                    "error": "Your Aadhaar is already verified.",
                    "masked_aadhaar": profile.aadhaar_masked,
                },
                status=400,
            )

        # --- Generate OTP & Send Email via SMTP ---------------------------
        otp = generate_demo_otp()
        send_aadhaar_otp_email(to_email=linked_email, otp=otp, masked_aadhaar=aadhaar_masked)
        otp_h = sha256_hash(otp)
        expiry = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # --- Persist hashed data only ------------------------------------
        profile.aadhaar_hash = aadhaar_h
        profile.aadhaar_masked = aadhaar_masked
        profile.linked_email = linked_email   # email is voluntary, not hashed
        profile.otp_hash = otp_h
        profile.otp_expires_at = expiry
        profile.otp_attempts = 0  # reset counter on new OTP
        profile.save(update_fields=[
            "aadhaar_hash", "aadhaar_masked", "linked_email",
            "otp_hash", "otp_expires_at", "otp_attempts", "updated_at",
        ])

        logger.info(
            "Aadhaar initiate: collector=%s, linked_email=%s, masked=%s, ref=%s [DEMO MODE]",
            request.user.email, linked_email, aadhaar_masked, profile.reference_id,
        )

        # --- Return reference ID to front-end -----------------------------
        return JsonResponse({
            "reference_id": str(profile.reference_id),
            "masked_aadhaar": aadhaar_masked,
            "linked_email": linked_email,
            "expires_in": OTP_EXPIRY_MINUTES * 60,  # seconds
            "demo_mode": True,
            "message": (
                f"OTP has been sent to {linked_email}. "
                f"Please check your inbox (or server console in demo mode)."
            ),
        })


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
class AadhaarVerifyView(View):
    """
    POST /api/collectors/aadhaar/verify/

    Verifies the OTP entered by the collector. On success, sets
    CollectorAadhaarProfile.aadhaar_verified = True and clears the OTP
    (single-use). Enforces a 5-minute expiry and max 3 attempts.

    Request body (JSON):
        { "reference_id": "<uuid>", "otp": "042817" }

    Responses:
        200 OK:
            { "verified": true, "masked_aadhaar": "XXXX XXXX 1964" }
        400 Bad Request:
            { "error": "<reason>", "attempts_remaining": <int> }
        403 Forbidden:
            { "error": "Only Collector accounts can use Aadhaar verification." }
    """

    def _check_collector(self, user):
        from trashport.users.models import User
        if user.role != User.Roles.COLLECTOR:
            return JsonResponse(
                {"error": "Only Collector accounts can use Aadhaar verification."},
                status=403,
            )
        return None

    def post(self, request, *args, **kwargs):
        # --- Scope guard -------------------------------------------------
        scope_err = self._check_collector(request.user)
        if scope_err:
            return scope_err

        # --- Parse body --------------------------------------------------
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        reference_id = str(data.get("reference_id", "")).strip()
        otp_entered = str(data.get("otp", "")).strip()

        if not reference_id or not otp_entered:
            return JsonResponse(
                {"error": "reference_id and otp are required."},
                status=400,
            )

        # --- Load profile by reference_id --------------------------------
        try:
            profile = CollectorAadhaarProfile.objects.get(
                reference_id=reference_id,
                collector=request.user,
            )
        except CollectorAadhaarProfile.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid or expired reference ID. Please restart the verification."},
                status=400,
            )

        # --- Already verified? -------------------------------------------
        if profile.aadhaar_verified:
            return JsonResponse({
                "verified": True,
                "masked_aadhaar": profile.aadhaar_masked,
                "message": "Already verified.",
            })

        # --- Rate limit check --------------------------------------------
        if profile.is_otp_locked():
            return JsonResponse(
                {
                    "error": (
                        "Maximum OTP attempts reached. "
                        "Please restart verification with your Aadhaar number."
                    ),
                    "attempts_remaining": 0,
                },
                status=400,
            )

        # --- Expiry check ------------------------------------------------
        if profile.is_otp_expired():
            return JsonResponse(
                {"error": "OTP has expired. Please request a new one.", "attempts_remaining": 0},
                status=400,
            )

        # --- OTP match check (compare hashes — never compare plaintext) --
        if not profile.otp_hash:
            return JsonResponse(
                {"error": "No pending OTP found. Please initiate verification first."},
                status=400,
            )

        entered_hash = sha256_hash(otp_entered)

        if entered_hash != profile.otp_hash:
            # Increment attempt counter
            profile.otp_attempts += 1
            profile.save(update_fields=["otp_attempts", "updated_at"])

            attempts_remaining = max(0, MAX_OTP_ATTEMPTS - profile.otp_attempts)
            logger.warning(
                "Aadhaar OTP mismatch: collector=%s, ref=%s, attempts=%d [DEMO MODE]",
                request.user.email, reference_id, profile.otp_attempts,
            )
            return JsonResponse(
                {
                    "error": f"Incorrect OTP. {attempts_remaining} attempt(s) remaining.",
                    "attempts_remaining": attempts_remaining,
                },
                status=400,
            )

        # --- SUCCESS — mark verified and clear OTP (single-use) ----------
        profile.aadhaar_verified = True
        profile.reset_otp()  # clears otp_hash, otp_expires_at, otp_attempts and saves aadhaar_verified=True

        # Also mark collector user verified and approved upon successful Aadhaar verification
        user = request.user
        user.is_verified = True
        user.verification_status = "APPROVED"
        user.save(update_fields=["is_verified", "verification_status"])

        logger.info(
            "Aadhaar verified: collector=%s, masked=%s [DEMO MODE]",
            user.email, profile.aadhaar_masked,
        )

        return JsonResponse({
            "verified": True,
            "masked_aadhaar": profile.aadhaar_masked,
            "message": "Aadhaar verification successful (DEMO MODE).",
            "demo_mode": True,
        })
