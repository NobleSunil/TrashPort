"""
trashport/citizens/views.py — Citizen Role View Layer
======================================================

PURPOSE:
  This file contains all view classes exclusively used by citizen users.
  These views are never called directly from the top-level URL config —
  they are dispatched to by the role-based system in waste_management/views.py
  or accessed directly through trashport/citizens/urls.py.

HOW THESE VIEWS ARE REACHED:
  1. Citizen visits /dashboard/
  2. DashboardView (waste_management/views.py) sees user.role == CITIZEN
  3. Delegates to CitizenDashboardView defined here
  Same pattern applies to: PickupRequestDetailView, PickupStatusUpdateView,
  ComplaintListView, ComplaintDetailView, PaymentCheckoutView, etc.

CONNECTION MAP:
  - waste_management/views.py       → dispatches most views here
  - waste_management/urls.py        → registers dispatcher URLs
  - trashport/citizens/urls.py      → registers citizen-specific extra URLs
                                      (wallet, redeem coupon, anonymous feedback)
  - waste_management/models.py      → Address, PickupRequest, Complaint, WasteCategory
  - trashport/payments/services.py  → PaymentGatewayService (card/UPI/wallet checkout)
  - trashport/payments/models.py    → PaymentTransaction, WalletHistory
  - trashport/notifications/models.py → Notification (in-app alerts on dashboard)

VIEW INVENTORY:
  CitizenDashboardView         : Main hub — active pickups, wallet, complaints, history.
  AddressListView              : List all saved addresses.
  AddressCreateView            : Register a new address with GPS map pin.
  AddressUpdateView            : Edit an existing address.
  AddressDeleteView            : Soft-delete (hides address, keeps for history integrity).
  CitizenPickupRequestCreateView : Book a new waste collection with address + category.
  CitizenPickupRequestDetailView : View details of a specific pickup.
  CitizenPickupStatusUpdateView  : Cancel, rate, or initiate payment on a pickup.
  CitizenComplaintListView     : List all complaints filed by this citizen.
  CitizenComplaintCreateView   : File a new complaint against a pickup.
  CitizenComplaintDetailView   : View a single complaint.
  CitizenPaymentCheckoutView   : Multi-method payment checkout (card/UPI/wallet).
  CitizenPaymentSuccessView    : Payment receipt display after successful payment.
  CitizenInvoiceView           : Printable tax invoice for a paid pickup.
  CitizenWalletView            : Recycling points wallet + coupon redemption.
  CitizenRedeemCouponView      : Convert 100 pts → Rs. 10 coupon stored in session.
  CitizenRemoveCouponView      : Cancel active coupon, refund 100 pts.
  SubmitAnonymousFeedbackView  : Accept anonymous feedback (no login required).

WALLET / COUPON FLOW:
  1. Citizen earns points when pickups are COMPLETED (via WalletService.adjust_points
     called in PickupRequest.save()).
  2. Citizen visits CitizenWalletView → sees balance and can redeem coupon.
  3. CitizenRedeemCouponView: deducts 100 pts → stores coupon in request.session.
  4. At CitizenPaymentCheckoutView: reads session coupon → applies Rs. 10 discount.
  5. CitizenRemoveCouponView: removes session coupon → refunds 100 pts.

IMPACT:
  - Changing CitizenPaymentCheckoutView affects the payment UX for ALL citizens.
  - Changing CitizenPickupRequestCreateView.form_valid() affects how pickups are created
    and how GPS coordinates are captured from the map.
  - Changing AddressDeleteView from soft-delete to hard-delete WILL break historical
    pickup records that reference deleted addresses (FK will be NULL).
"""

"""
Citizen-specific views for managing user addresses, booking pickup requests, paying bills, and logging complaints.
"""

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from waste_management.models import Address, Complaint, PickupRequest, WasteCategory
from .forms import AddressForm, ComplaintForm, PickupRequestForm
from trashport.payments.services import PaymentGatewayService, WalletService
from trashport.payments.models import PaymentTransaction, WalletHistory


class CitizenDashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the Citizen Dashboard.
    Displays:
    - Active pickup requests (Pending, Assigned, In Transit).
    - Wallet points.
    - Active subscription and list of plans.
    - Historical completed pickup requests.
    - Complaints logged by the citizen.
    """
    template_name = "citizen/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role

        # Active pickups that are not completed and not cancelled (newest first)
        context["active_pickups"] = PickupRequest.objects.filter(
            citizen=user
        ).exclude(
            status__in=[PickupRequest.StatusChoices.COMPLETED, PickupRequest.StatusChoices.CANCELLED]
        ).select_related("category", "address", "collector").order_by("-created_at")

        # History of completed and cancelled pickups
        history_pickups = PickupRequest.objects.filter(
            citizen=user,
            status__in=[PickupRequest.StatusChoices.COMPLETED, PickupRequest.StatusChoices.CANCELLED]
        ).select_related("category", "address", "collector").order_by("-updated_at")
        context["history_pickups"] = history_pickups
        context["past_pickups"] = history_pickups.filter(status=PickupRequest.StatusChoices.COMPLETED)
        context["cancelled_pickups"] = history_pickups.filter(status=PickupRequest.StatusChoices.CANCELLED)
        context["completed_count"] = context["past_pickups"].count()
        context["cancelled_count"] = context["cancelled_pickups"].count()
        context["history_count"] = history_pickups.count()

        context["addresses"] = Address.objects.filter(user=user, is_hidden=False)
        context["complaints"] = Complaint.objects.filter(citizen=user).select_related("pickup_request").order_by("-created_at")[:10]

        context["waste_categories"] = WasteCategory.objects.all().order_by("name")

        # Statistics & Metrics
        total_recycled = PickupRequest.objects.filter(
            citizen=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).aggregate(total=Sum("weight_kg"))["total"] or Decimal("0.00")

        context["total_recycled_kg"] = total_recycled
        context["active_count"] = context["active_pickups"].count()
        context["pending_payment_count"] = context["active_pickups"].filter(
            status=PickupRequest.StatusChoices.AWAITING_PAYMENT
        ).count()
        # Completed payment transactions for the citizen
        context["payment_transactions"] = PaymentTransaction.objects.filter(
            user=user,
            status=PaymentTransaction.Statuses.COMPLETED
        ).order_by("-created_at")
        context["transaction_count"] = context["payment_transactions"].count()

        # Paid pickup requests eligible for tax invoices
        context["paid_pickups"] = PickupRequest.objects.filter(
            citizen=user,
            is_paid=True
        ).select_related("category", "address").order_by("-updated_at")
        context["invoice_count"] = context["paid_pickups"].count()

        # In-app notifications for the citizen
        from trashport.notifications.models import Notification
        user_notifications = Notification.objects.filter(user=user).order_by("-created_at")
        context["notifications"] = user_notifications[:20]
        context["unread_notifications_count"] = user_notifications.filter(is_read=False).count()

        return context



# ==============================================================================
# Address CRUD Views
# ==============================================================================

class AddressListView(LoginRequiredMixin, ListView):
    """
    Lists all saved addresses for the logged-in citizen.
    """
    model = Address
    template_name = "citizen/address_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        # Filter addresses to only show those belonging to the current user
        return Address.objects.filter(user=self.request.user, is_hidden=False).order_by("-is_default", "-created_at")


class AddressCreateView(LoginRequiredMixin, CreateView):
    """
    Allows a citizen to register a new address.
    """
    model = Address
    form_class = AddressForm
    template_name = "citizen/address_form.html"
    success_url = reverse_lazy("waste_management:address_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Address added successfully!")
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows a citizen to modify an existing saved address.
    """
    model = Address
    form_class = AddressForm
    template_name = "citizen/address_form.html"
    success_url = reverse_lazy("waste_management:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user, is_hidden=False)

    def form_valid(self, form):
        messages.success(self.request, "Address updated successfully!")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, View):
    """
    Soft-deletes an address by setting is_hidden=True.
    The record is retained in the database (for historical pickup data) but
    disappears from all citizen-facing views.
    """

    def get(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user, is_hidden=False)
        return render(request, "citizen/address_confirm_delete.html", {"object": address})

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user, is_hidden=False)
        # If this was the default address, clear the flag before hiding
        if address.is_default:
            address.is_default = False
        address.is_hidden = True
        address.save(update_fields=["is_hidden", "is_default"])
        messages.success(request, "Address removed successfully.")
        return redirect("waste_management:address_list")


# ==============================================================================
# Pickup Request Views
# ==============================================================================

class CitizenPickupRequestCreateView(LoginRequiredMixin, CreateView):
    """
    Allows a citizen to request a waste collection.
    Form requires address selection (only displays user's addresses), waste category,
    weight estimate (weight_kg), quantity estimate, and scheduled date/time.
    """
    model = PickupRequest
    form_class = PickupRequestForm
    template_name = "citizen/pickup_form.html"
    success_url = reverse_lazy("waste_management:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_addresses = Address.objects.filter(user=self.request.user, is_hidden=False)
        context["addresses"] = user_addresses
        import json
        addresses_data = {}
        for addr in user_addresses:
            if addr.latitude is not None and addr.longitude is not None:
                addresses_data[str(addr.id)] = {
                    "lat": float(addr.latitude),
                    "lng": float(addr.longitude),
                    "line1": addr.address_line1,
                    "city": addr.city,
                    "postal_code": addr.postal_code,
                }
        context["addresses_json"] = json.dumps(addresses_data)

        categories_data = {}
        for cat in WasteCategory.objects.all():
            categories_data[str(cat.id)] = {
                "name": cat.name,
                "fee_per_kg": float(cat.fee_per_kg),
                "max_weight_kg": float(cat.max_weight_kg if cat.max_weight_kg is not None else 100.00),
            }
        context["categories_json"] = json.dumps(categories_data)
        return context

    def form_valid(self, form):
        form.instance.citizen = self.request.user
        submitted_lat = form.cleaned_data.get("latitude")
        submitted_lng = form.cleaned_data.get("longitude")

        # If no saved address was selected, create a new Address from inline inputs
        if not form.cleaned_data.get("address"):
            addr = Address.objects.create(
                user=self.request.user,
                address_line1=form.cleaned_data.get("new_address_line1") or "Specified Map Location",
                city=form.cleaned_data.get("new_city") or "Kochi",
                state="Kerala",
                postal_code=form.cleaned_data.get("new_postal_code") or "682001",
                latitude=submitted_lat,
                longitude=submitted_lng,
                is_default=not Address.objects.filter(user=self.request.user).exists(),
            )
            form.instance.address = addr
            form.instance.latitude = submitted_lat
            form.instance.longitude = submitted_lng
        else:
            selected_addr = form.cleaned_data.get("address")
            form.instance.address = selected_addr
            if submitted_lat and submitted_lng:
                form.instance.latitude = submitted_lat
                form.instance.longitude = submitted_lng
                if selected_addr and (selected_addr.latitude is None or selected_addr.longitude is None):
                    selected_addr.latitude = submitted_lat
                    selected_addr.longitude = submitted_lng
                    selected_addr.save(update_fields=["latitude", "longitude"])
            elif selected_addr and selected_addr.latitude is not None:
                form.instance.latitude = selected_addr.latitude
                form.instance.longitude = selected_addr.longitude

        messages.success(self.request, "Pickup request booked successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("waste_management:pickup_detail", kwargs={"pk": self.object.pk}) + "?just_booked=true"


class CitizenPickupRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Displays the details of a single pickup request.
    Citizens can only view their own requests.
    """
    model = PickupRequest
    template_name = "citizen/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        return PickupRequest.objects.filter(citizen=self.request.user)


class CitizenPickupStatusUpdateView(LoginRequiredMixin, View):
    """
    Handles Citizen-specific actions on a pickup request via POST.
    Supported actions:
    - feedback: Citizen rates the service (1-5 stars) and adds comments.
    - cancel: Cancels the request (only if it is still PENDING or AWAITING_PAYMENT).
    - pay: Citizen settles the collection bill.
    """
    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk, citizen=request.user)
        action = request.POST.get("action")

        if action == "feedback":
            rating = request.POST.get("rating")
            comments = request.POST.get("comments")
            if rating:
                pickup.feedback_rating = int(rating)
                pickup.feedback_comments = comments
                pickup.save()
                messages.success(request, "Thank you for your feedback!")
        elif action == "cancel":
            # 1. Prevent cancellation if a collector is already assigned or request is in progress
            if pickup.collector is not None or pickup.status in [
                PickupRequest.StatusChoices.ASSIGNED,
                PickupRequest.StatusChoices.IN_TRANSIT,
                PickupRequest.StatusChoices.COMPLETED
            ]:
                messages.error(
                    request,
                    "This pickup request cannot be cancelled because a collector has already been assigned to it."
                )
                return redirect("waste_management:pickup_detail", pk=pk)

            # 2. Only allow cancellation if still PENDING or AWAITING_PAYMENT
            if pickup.status not in [PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT]:
                messages.error(request, "This pickup cannot be cancelled in its current status.")
                return redirect("waste_management:pickup_detail", pk=pk)

            # 3. User must specify a reason why cancelled
            reason = request.POST.get("cancellation_reason", "").strip()
            if not reason:
                messages.error(request, "Please specify a reason for cancelling your pickup request.")
                return redirect("waste_management:pickup_detail", pk=pk)

            pickup.status = PickupRequest.StatusChoices.CANCELLED
            pickup.cancellation_reason = reason
            pickup.cancelled_at = timezone.now()
            pickup.save(update_fields=["status", "cancellation_reason", "cancelled_at"])

            # 4. Handle refund notice if payment was already made
            if pickup.is_paid:
                refund_msg = (
                    f"Your pickup request #{pickup.display_id} has been cancelled. "
                    f"Your payment of Rs. {pickup.fee} will be refunded to your original payment method within 3 to 7 business days."
                )
                messages.warning(request, refund_msg)

                # Send in-app notification to the citizen
                try:
                    from trashport.notifications.models import Notification
                    from trashport.notifications.services import NotificationService
                    NotificationService.create_notification(
                        user=request.user,
                        title=f"Pickup #{pickup.display_id} Cancelled — Refund Initiated",
                        message=f"Pickup #{pickup.display_id} was cancelled ({reason}). Your refund of Rs. {pickup.fee} will be credited to your original payment method within 3 to 7 business days.",
                        notification_type=Notification.Types.PAYMENT
                    )
                except Exception:
                    pass
            else:
                messages.warning(request, f"Your pickup request #{pickup.display_id} has been cancelled.")
        elif action == "pay" and pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT:
            # Redirect to the full payment checkout flow
            return redirect("waste_management:payment_checkout", pk=pk)

        return redirect("waste_management:pickup_detail", pk=pk)




# ==============================================================================
# Complaint Views
# ==============================================================================

class CitizenComplaintListView(LoginRequiredMixin, ListView):
    """
    Lists all complaints registered by this citizen.
    """
    model = Complaint
    template_name = "citizen/complaint_list.html"
    context_object_name = "complaints"

    def get_queryset(self):
        return Complaint.objects.filter(citizen=self.request.user).order_by("-created_at")


class CitizenComplaintCreateView(LoginRequiredMixin, CreateView):
    """
    Allows a citizen to file a complaint against a specific pickup request.
    """
    model = Complaint
    form_class = ComplaintForm
    template_name = "citizen/complaint_form.html"
    success_url = reverse_lazy("waste_management:complaint_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.citizen = self.request.user
        form.instance.status = Complaint.StatusChoices.PENDING
        messages.success(self.request, "Complaint filed successfully!")
        return super().form_valid(form)


class CitizenComplaintDetailView(LoginRequiredMixin, DetailView):
    """
    Displays detail information of a single complaint filed by this citizen.
    """
    model = Complaint
    template_name = "citizen/complaint_detail.html"
    context_object_name = "complaint"

    def get_queryset(self):
        return Complaint.objects.filter(citizen=self.request.user)


# ==============================================================================
# Payment Checkout & Receipt Views
# ==============================================================================

class CitizenPaymentCheckoutView(LoginRequiredMixin, View):
    """
    GET  — Renders the payment checkout page for a pickup request that
            requires payment (status = AWAITING_PAYMENT, is_paid = False).
    POST — Routes the payment to the appropriate PaymentGatewayService method
            based on the selected payment_method (card / upi / wallet).
    """
    template_name = "citizen/payment_checkout.html"

    def _get_pickup(self, request, pk):
        return get_object_or_404(
            PickupRequest,
            pk=pk,
            citizen=request.user,
            status=PickupRequest.StatusChoices.AWAITING_PAYMENT,
            is_paid=False,
        )

    def _build_checkout_context(self, request, pickup, error_msg=None, active_method="card"):
        """Construct checkout page context including wallet points, coupons, and test cards (DRY pattern)."""
        wallet_points = getattr(request.user, "wallet_points", 0)
        wallet_value_inr = Decimal(str(wallet_points)) * Decimal("0.10")
        coupon = request.session.get("wallet_coupon")
        discount = Decimal(str(coupon["discount"])) if coupon else Decimal("0.00")
        discounted_fee = max(Decimal("0.00"), Decimal(str(pickup.fee)) - discount)
        can_redeem_points = (wallet_points >= 100 and not coupon)

        context = {
            "pickup": pickup,
            "wallet_points": wallet_points,
            "wallet_value_inr": wallet_value_inr,
            "wallet_covers_fee": wallet_value_inr >= discounted_fee,
            "coupon": coupon,
            "discount": discount,
            "discounted_fee": discounted_fee,
            "can_redeem_points": can_redeem_points,
            "test_cards": [
                {"number": "4242 4242 4242 4242", "brand": "Visa", "result": "Always succeeds"},
                {"number": "5555 5555 5555 4444", "brand": "Mastercard", "result": "Always succeeds"},
                {"number": "4000 0000 0000 0002", "brand": "Visa", "result": "Card declined"},
                {"number": "4000 0000 0000 9995", "brand": "Visa", "result": "Insufficient funds"},
            ],
        }
        if error_msg:
            context["error"] = error_msg
            context["active_method"] = active_method
        return context

    def get(self, request, pk, *args, **kwargs):
        pickup = self._get_pickup(request, pk)
        return render(request, self.template_name, self._build_checkout_context(request, pickup))

    def post(self, request, pk, *args, **kwargs):
        pickup = self._get_pickup(request, pk)
        method = request.POST.get("payment_method", "card")
        result = None

        # Apply coupon discount if present
        coupon = request.session.get("wallet_coupon")
        discount = Decimal(str(coupon["discount"])) if coupon else Decimal("0.00")
        original_fee = Decimal(str(pickup.fee))
        discounted_fee = max(Decimal("0.00"), original_fee - discount)

        if discounted_fee == Decimal("0.00"):
            pickup.fee = Decimal("0.00")
            result = PaymentGatewayService.process_wallet_payment(
                user=request.user,
                pickup=pickup,
            )
        elif method == "card":
            card_number = request.POST.get("card_number", "").strip()
            card_name = request.POST.get("card_name", "").strip()
            expiry = request.POST.get("expiry", "").strip()
            cvv = request.POST.get("cvv", "").strip()

            if not card_number or not card_name or not expiry or not cvv:
                context = self._build_checkout_context(
                    request,
                    pickup,
                    error_msg="All card details (Card Number, Name on Card, Expiry Date, CVV) are mandatory.",
                    active_method="card"
                )
                return render(request, self.template_name, context)

            pickup.fee = discounted_fee
            result = PaymentGatewayService.process_card_payment(
                user=request.user,
                pickup=pickup,
                card_number=card_number,
                card_name=card_name,
                expiry=expiry,
                cvv=cvv,
            )
        elif method == "upi":
            upi_id = request.POST.get("upi_id", "").strip()
            if not upi_id:
                context = self._build_checkout_context(
                    request,
                    pickup,
                    error_msg="UPI ID is mandatory to proceed with payment.",
                    active_method="upi"
                )
                return render(request, self.template_name, context)

            pickup.fee = discounted_fee
            result = PaymentGatewayService.process_upi_payment(
                user=request.user,
                pickup=pickup,
                upi_id=upi_id,
            )
        elif method == "wallet":
            pickup.fee = discounted_fee
            result = PaymentGatewayService.process_wallet_payment(
                user=request.user,
                pickup=pickup,
            )
        else:
            messages.error(request, "Invalid payment method selected.")
            return redirect("waste_management:payment_checkout", pk=pk)

        if result and result["success"]:
            if coupon:
                request.session.pop("wallet_coupon", None)
            request.session[f"payment_result_{pk}"] = {
                "transaction_id": result["transaction_id"],
                "amount": result["amount"],
                "method": result["method"],
                "card_last4": result.get("card_last4"),
                "upi_id": result.get("upi_id"),
                "points_used": result.get("points_used"),
                "coupon_discount": float(discount) if coupon else None,
                "coupon_code": coupon["code"] if coupon else None,
            }
            return redirect("waste_management:payment_success", pk=pk)
        else:
            error_msg = result.get("error_message", "Payment failed. Please try again.") if result else "Payment processing error."
            context = self._build_checkout_context(request, pickup, error_msg=error_msg, active_method=method)
            return render(request, self.template_name, context)




class CitizenPaymentSuccessView(LoginRequiredMixin, View):
    """
    Displays a payment success receipt page after a successful payment.
    Reads result data from the session and also fetches the PaymentTransaction
    record for display.
    """
    def get(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk, citizen=request.user)
        session_key = f"payment_result_{pk}"
        result = request.session.pop(session_key, None)

        # Fetch the most recent completed transaction for this pickup
        transaction = PaymentTransaction.objects.filter(
            user=request.user,
            description__icontains=f"Pickup #{pickup.id}",
            status=PaymentTransaction.Statuses.COMPLETED,
        ).order_by("-created_at").first()

        return render(request, "citizen/payment_success.html", {
            "pickup": pickup,
            "result": result,
            "transaction": transaction,
        })


class CitizenInvoiceView(LoginRequiredMixin, View):
    """
    Renders and allows printing/downloading an official Tax Invoice / Payment Receipt
    for a paid pickup request.
    Restricted to the request's owner (citizen) or an administrator.
    """
    template_name = "citizen/invoice.html"

    def get(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(
            PickupRequest.objects.select_related("citizen", "category", "address", "collector"),
            pk=pk,
        )

        # Authorization check: owner or admin/superuser
        if pickup.citizen != request.user and not (getattr(request.user, "role", "") == "ADMIN" or request.user.is_superuser):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have permission to view this invoice.")

        # Check if pickup is paid
        if not pickup.is_paid:
            messages.warning(request, "This pickup has not been paid for yet. Please complete payment to view the invoice.")
            if pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT:
                return redirect("waste_management:payment_checkout", pk=pickup.pk)
            return redirect("waste_management:pickup_detail", pk=pickup.pk)

        # Retrieve matching completed payment transaction
        transaction = PaymentTransaction.objects.filter(
            user=pickup.citizen,
            description__icontains=f"Pickup #{pickup.id}",
            status=PaymentTransaction.Statuses.COMPLETED,
        ).order_by("-created_at").first()

        # Compute line-item breakdown
        base_rate = pickup.category.fee_per_kg if pickup.category else Decimal("0.00")
        base_amount = Decimal(str(pickup.weight_kg)) * Decimal(str(base_rate))
        extra_fee = pickup.extra_fee or Decimal("0.00")
        total_amount = pickup.fee

        # Invoice number format: INV-YYYY-00000{id}
        invoice_year = pickup.created_at.year if pickup.created_at else timezone.now().year
        invoice_number = f"INV-{invoice_year}-{pickup.id:05d}"

        return render(request, self.template_name, {
            "pickup": pickup,
            "transaction": transaction,
            "invoice_number": invoice_number,
            "invoice_date": transaction.created_at if transaction else pickup.updated_at,
            "base_rate": base_rate,
            "base_amount": base_amount,
            "extra_fee": extra_fee,
            "total_amount": total_amount,
        })


# ==============================================================================
# Wallet Views
# ==============================================================================

class CitizenWalletView(LoginRequiredMixin, TemplateView):
    """
    Displays the citizen's wallet: point history and a coupon redemption option.
    When the user has >= 100 points, they can redeem 100 pts for a Rs. 10 discount.
    """
    template_name = "citizen/wallet.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        points = getattr(user, "wallet_points", 0)
        context["wallet_points"] = points
        context["can_redeem"] = points >= 100

        # If user has points but no history recorded yet, initialize an entry
        history_qs = WalletHistory.objects.filter(user=user).order_by("-created_at")
        if points > 0 and not history_qs.exists():
            WalletHistory.objects.create(
                user=user,
                points_delta=points,
                reason="Initial Green Wallet Bonus & Recycling Incentive",
            )
            history_qs = WalletHistory.objects.filter(user=user).order_by("-created_at")

        context["history"] = history_qs[:50]
        # Check if there's an active coupon in session
        context["active_coupon"] = self.request.session.get("wallet_coupon")
        return context


class CitizenRedeemCouponView(LoginRequiredMixin, View):
    """
    POST — Deducts 100 wallet points and stores a Rs. 10 coupon in the session.
    The coupon can then be applied at any pickup payment checkout (reducing Rs. 10 from total cost).
    Supports redirecting back to checkout via 'next' query or form parameter.
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        wallet_points = getattr(user, "wallet_points", 0)
        next_url = request.POST.get("next") or request.GET.get("next")

        if wallet_points < 100:
            messages.error(request, "You need at least 100 wallet points to redeem a discount.")
            return redirect(next_url or "citizens:wallet")

        # Check if user already has an active coupon
        if request.session.get("wallet_coupon"):
            messages.warning(request, "You already have an active Rs. 10 discount coupon. Use it before redeeming another.")
            return redirect(next_url or "citizens:wallet")

        # Deduct 100 points and issue coupon
        import uuid
        coupon_code = f"TP{uuid.uuid4().hex[:8].upper()}"
        WalletService.adjust_points(
            user=user,
            points_delta=-100,
            reason=f"Redeemed 100 pts for Rs.10 discount ({coupon_code})",
        )
        request.session["wallet_coupon"] = {
            "code": coupon_code,
            "discount": 10,
        }
        messages.success(request, f"100 points redeemed! You get Rs. 10 off your purchase (Coupon: {coupon_code}).")
        return redirect(next_url or "citizens:wallet")


class CitizenRemoveCouponView(LoginRequiredMixin, View):
    """
    Cancels an active coupon in the session and refunds the 100 points back to the user's wallet.
    """
    def get(self, request, *args, **kwargs):
        return self._cancel(request)

    def post(self, request, *args, **kwargs):
        return self._cancel(request)

    def _cancel(self, request):
        coupon = request.session.pop("wallet_coupon", None)
        if coupon:
            WalletService.adjust_points(
                user=request.user,
                points_delta=100,
                reason=f"Refunded 100 pts from cancelled coupon ({coupon.get('code')})",
            )
            messages.info(request, "Coupon removed and 100 points refunded to your wallet.")
        next_url = request.POST.get("next") or request.GET.get("next")
        return redirect(next_url or "citizens:wallet")


from django.http import JsonResponse
from waste_management.models import AnonymousFeedback

class SubmitAnonymousFeedbackView(View):
    """
    Accepts anonymous feedback from citizens and website visitors.
    No login required. Saves submission directly into database for admin inspection.
    Supports both JSON AJAX requests and regular form POST requests.
    """
    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.content_type == "application/json"

        if request.content_type == "application/json":
            import json
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                data = {}
        else:
            data = request.POST

        category = data.get("category", AnonymousFeedback.CategoryChoices.GENERAL)
        subject = data.get("subject", "").strip()
        message_text = data.get("message", "").strip()

        if not message_text:
            if is_ajax:
                return JsonResponse({"status": "error", "message": "Please write your feedback message before sending."}, status=400)
            messages.error(request, "Feedback message cannot be blank.")
            return redirect(request.META.get("HTTP_REFERER", "home"))

        feedback_obj = AnonymousFeedback.objects.create(
            category=category,
            subject=subject or f"Anonymous Report ({category})",
            message=message_text,
        )

        if is_ajax:
            return JsonResponse({
                "status": "success",
                "message": "Thank you! Your anonymous feedback has been delivered directly to our administrative team.",
                "id": feedback_obj.id,
            }, status=200)

        messages.success(request, "Thank you! Your anonymous feedback has been safely submitted to the administrators.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

