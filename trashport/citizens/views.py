"""
Citizen-specific views for managing user addresses, booking pickup requests, paying bills, and logging complaints.
"""

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

from waste_management.models import Address, Complaint, PickupRequest, SubscriptionTier, Subscription
from .forms import AddressForm, ComplaintForm, PickupRequestForm


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

        # Active pickups that are not completed and not cancelled
        context["active_pickups"] = PickupRequest.objects.filter(
            citizen=user
        ).exclude(status=PickupRequest.StatusChoices.COMPLETED).exclude(status=PickupRequest.StatusChoices.CANCELLED).order_by("-schedule_date")
        
        # History of completed pickups
        context["past_pickups"] = PickupRequest.objects.filter(
            citizen=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).order_by("-schedule_date")
        
        context["addresses"] = Address.objects.filter(user=user)
        context["complaints"] = Complaint.objects.filter(citizen=user).order_by("-created_at")
        
        # Subscription details
        context["subscription"] = Subscription.objects.filter(user=user, is_active=True).first()
        context["available_tiers"] = SubscriptionTier.objects.filter(is_active=True)

        # Statistics & Metrics
        total_recycled = PickupRequest.objects.filter(
            citizen=user,
            status=PickupRequest.StatusChoices.COMPLETED
        ).aggregate(total=Sum("weight_kg"))["total"] or Decimal("0.00")

        context["total_recycled_kg"] = total_recycled
        context["active_count"] = context["active_pickups"].count()
        context["completed_count"] = context["past_pickups"].count()
        context["pending_payment_count"] = context["active_pickups"].filter(
            status=PickupRequest.StatusChoices.AWAITING_PAYMENT
        ).count()
        context["address_count"] = context["addresses"].count()

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
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")


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
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Address updated successfully!")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """
    Allows a citizen to delete a saved address.
    """
    model = Address
    template_name = "citizen/address_confirm_delete.html"
    success_url = reverse_lazy("waste_management:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Address deleted successfully!")
        return super().delete(request, *args, **kwargs)


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

    def form_valid(self, form):
        form.instance.citizen = self.request.user
        messages.success(self.request, "Pickup request booked successfully!")
        return super().form_valid(form)


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
        elif action == "cancel" and pickup.status in [PickupRequest.StatusChoices.PENDING, PickupRequest.StatusChoices.AWAITING_PAYMENT]:
            pickup.status = PickupRequest.StatusChoices.CANCELLED
            pickup.save()
            messages.warning(request, "Your pickup request has been cancelled.")
        elif action == "pay" and pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT:
            pickup.is_paid = True
            pickup.status = PickupRequest.StatusChoices.PENDING
            pickup.save()
            messages.success(request, f"Payment of ${pickup.fee:.2f} processed successfully! Your request is now pending assignment.")

        return redirect("waste_management:pickup_detail", pk=pk)


# ==============================================================================
# Subscription View
# ==============================================================================

class CitizenSubscribeView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        tier = get_object_or_404(SubscriptionTier, pk=pk)
        user = request.user

        # Deactivate old subscriptions
        Subscription.objects.filter(user=user, is_active=True).update(is_active=False)

        # Create new subscription
        Subscription.objects.create(
            user=user,
            tier=tier,
            start_date=timezone.now().date(),
            is_active=True
        )
        messages.success(request, f"Successfully subscribed to {tier.name}!")
        return redirect("waste_management:dashboard")


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
