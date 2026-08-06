from rest_framework import viewsets, permissions as drf_permissions
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Address, SubscriptionTier, Subscription, WasteCategory, PickupRequest, Complaint
from .serializers import (
    AddressSerializer,
    SubscriptionTierSerializer,
    SubscriptionSerializer,
    WasteCategorySerializer,
    PickupRequestSerializer,
    ComplaintSerializer,
)
from .forms import AddressForm, PickupRequestForm, ComplaintForm, WasteCategoryForm, SubscriptionTierForm

User = get_user_model()

# ==============================================================================
# REST API Viewsets (for DRF)
# ==============================================================================

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all().order_by("-created_at")
    serializer_class = AddressSerializer
    permission_classes = [drf_permissions.AllowAny]


class SubscriptionTierViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionTier.objects.all().order_by("price")
    serializer_class = SubscriptionTierSerializer
    permission_classes = [drf_permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all().order_by("-created_at")
    serializer_class = SubscriptionSerializer
    permission_classes = [drf_permissions.AllowAny]


class WasteCategoryViewSet(viewsets.ModelViewSet):
    queryset = WasteCategory.objects.all().order_by("name")
    serializer_class = WasteCategorySerializer
    permission_classes = [drf_permissions.AllowAny]


class PickupRequestViewSet(viewsets.ModelViewSet):
    queryset = PickupRequest.objects.all().order_by("-schedule_date")
    serializer_class = PickupRequestSerializer
    permission_classes = [drf_permissions.AllowAny]


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all().order_by("-created_at")
    serializer_class = ComplaintSerializer
    permission_classes = [drf_permissions.AllowAny]


# ==============================================================================
# Template-Based Web UI Views
# ==============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "waste_management/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Common stats
        context["role"] = user.role

        if user.role == User.Roles.CITIZEN:
            context["active_pickups"] = PickupRequest.objects.filter(
                citizen=user
            ).exclude(status=PickupRequest.StatusChoices.COMPLETED).exclude(status=PickupRequest.StatusChoices.CANCELLED).order_by("-schedule_date")
            context["past_pickups"] = PickupRequest.objects.filter(
                citizen=user,
                status=PickupRequest.StatusChoices.COMPLETED
            ).order_by("-schedule_date")
            context["addresses"] = Address.objects.filter(user=user)
            context["complaints"] = Complaint.objects.filter(citizen=user).order_by("-created_at")
            
            # Active subscription
            active_sub = Subscription.objects.filter(user=user, is_active=True).first()
            context["subscription"] = active_sub
            context["available_tiers"] = SubscriptionTier.objects.filter(is_active=True)

        elif user.role == User.Roles.COLLECTOR:
            context["assigned_pickups"] = PickupRequest.objects.filter(
                collector=user,
                status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]
            ).order_by("schedule_date")
            
            context["completed_pickups"] = PickupRequest.objects.filter(
                collector=user,
                status=PickupRequest.StatusChoices.COMPLETED
            ).order_by("-schedule_date")
            
            # Unassigned pending requests in system
            context["unassigned_pickups"] = PickupRequest.objects.filter(
                status=PickupRequest.StatusChoices.PENDING
            ).order_by("schedule_date")

        elif user.role == User.Roles.ADMIN:
            context["total_pickups"] = PickupRequest.objects.count()
            context["pending_pickups"] = PickupRequest.objects.filter(status=PickupRequest.StatusChoices.PENDING).count()
            context["active_complaints"] = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).count()
            context["total_citizens"] = User.objects.filter(role=User.Roles.CITIZEN).count()
            context["total_collectors"] = User.objects.filter(role=User.Roles.COLLECTOR).count()
            
            context["complaints"] = Complaint.objects.filter(status=Complaint.StatusChoices.PENDING).order_by("-created_at")
            context["recent_pickups"] = PickupRequest.objects.all().order_by("-created_at")[:10]
            context["categories"] = WasteCategory.objects.all()
            context["tiers"] = SubscriptionTier.objects.all()

        return context


# --- Address Views ---

class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = "waste_management/address_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by("-is_default", "-created_at")


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = "waste_management/address_form.html"
    success_url = reverse_lazy("waste_management:address_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Address added successfully!")
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = "waste_management/address_form.html"
    success_url = reverse_lazy("waste_management:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Address updated successfully!")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = Address
    template_name = "waste_management/address_confirm_delete.html"
    success_url = reverse_lazy("waste_management:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Address deleted successfully!")
        return super().delete(request, *args, **kwargs)


# --- Pickup Request Views ---

class PickupRequestCreateView(LoginRequiredMixin, CreateView):
    model = PickupRequest
    form_class = PickupRequestForm
    template_name = "waste_management/pickup_form.html"
    success_url = reverse_lazy("waste_management:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.citizen = self.request.user
        messages.success(self.request, "Pickup request booked successfully!")
        return super().form_valid(form)


class PickupRequestDetailView(LoginRequiredMixin, DetailView):
    model = PickupRequest
    template_name = "waste_management/pickup_detail.html"
    context_object_name = "pickup"

    def get_queryset(self):
        # Citizens can only view their own; Collectors and Admins can view any
        user = self.request.user
        if user.role == User.Roles.CITIZEN:
            return PickupRequest.objects.filter(citizen=user)
        return PickupRequest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.role == User.Roles.ADMIN:
            context["collectors"] = User.objects.filter(role=User.Roles.COLLECTOR)
        return context


class PickupStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        pickup = get_object_or_404(PickupRequest, pk=pk)
        action = request.POST.get("action")
        user = request.user

        if user.role == User.Roles.COLLECTOR:
            if action == "claim":
                pickup.collector = user
                pickup.status = PickupRequest.StatusChoices.ASSIGNED
                pickup.save()
                messages.success(request, "Pickup claimed successfully!")
            elif action == "transit" and pickup.collector == user:
                pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
                pickup.save()
                messages.success(request, "Status updated to In Transit.")
            elif action == "complete" and pickup.collector == user:
                pickup.status = PickupRequest.StatusChoices.COMPLETED
                pickup.save()
                messages.success(request, "Pickup completed successfully!")
            elif action == "cancel" and pickup.collector == user:
                # Release it back to pending or cancel
                pickup.status = PickupRequest.StatusChoices.PENDING
                pickup.collector = None
                pickup.save()
                messages.warning(request, "Job released. Status reverted to Pending.")
        
        elif user.role == User.Roles.ADMIN:
            # Admins can manually set any status or assign any collector
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

        # Citizen rating/feedback, cancel, or payment
        elif user.role == User.Roles.CITIZEN and pickup.citizen == user:
            if action == "pay" and pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT:
                pickup.is_paid = True
                pickup.status = PickupRequest.StatusChoices.PENDING
                pickup.save()
                messages.success(request, f"Payment of ${pickup.fee} processed successfully! Your request is now pending assignment.")
            elif action == "feedback":
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

        return redirect("waste_management:pickup_detail", pk=pk)


# --- Complaint Views ---

class ComplaintListView(LoginRequiredMixin, ListView):
    model = Complaint
    template_name = "waste_management/complaint_list.html"
    context_object_name = "complaints"

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Roles.CITIZEN:
            return Complaint.objects.filter(citizen=user).order_by("-created_at")
        elif user.role == User.Roles.ADMIN:
            return Complaint.objects.all().order_by("-created_at")
        return Complaint.objects.none()


class ComplaintCreateView(LoginRequiredMixin, CreateView):
    model = Complaint
    form_class = ComplaintForm
    template_name = "waste_management/complaint_form.html"
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


class ComplaintDetailView(LoginRequiredMixin, DetailView):
    model = Complaint
    template_name = "waste_management/complaint_detail.html"
    context_object_name = "complaint"

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Roles.CITIZEN:
            return Complaint.objects.filter(citizen=user)
        elif user.role == User.Roles.ADMIN:
            return Complaint.objects.all()
        return Complaint.objects.none()

    def post(self, request, *args, **kwargs):
        # Only admins can resolve complaints
        complaint = self.get_object()
        if request.user.role == User.Roles.ADMIN:
            action = request.POST.get("action")
            if action == "resolve":
                complaint.status = Complaint.StatusChoices.RESOLVED
                complaint.save()
                messages.success(request, "Complaint marked as resolved.")
        return redirect("waste_management:complaint_detail", pk=complaint.pk)


# --- Admin Master Entries CRUD ---

class WasteCategoryListView(LoginRequiredMixin, ListView):
    model = WasteCategory
    template_name = "waste_management/category_list.html"
    context_object_name = "categories"


class WasteCategoryCreateView(LoginRequiredMixin, CreateView):
    model = WasteCategory
    form_class = WasteCategoryForm
    template_name = "waste_management/category_form.html"
    success_url = reverse_lazy("waste_management:category_list")

    def form_valid(self, form):
        messages.success(self.request, "Waste Category created!")
        return super().form_valid(form)


class WasteCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = WasteCategory
    form_class = WasteCategoryForm
    template_name = "waste_management/category_form.html"
    success_url = reverse_lazy("waste_management:category_list")

    def form_valid(self, form):
        messages.success(self.request, "Waste Category updated!")
        return super().form_valid(form)


class SubscriptionTierListView(LoginRequiredMixin, ListView):
    model = SubscriptionTier
    template_name = "waste_management/tier_list.html"
    context_object_name = "tiers"


class SubscriptionTierCreateView(LoginRequiredMixin, CreateView):
    model = SubscriptionTier
    form_class = SubscriptionTierForm
    template_name = "waste_management/tier_form.html"
    success_url = reverse_lazy("waste_management:tier_list")

    def form_valid(self, form):
        messages.success(self.request, "Subscription Tier created!")
        return super().form_valid(form)


class SubscriptionTierUpdateView(LoginRequiredMixin, UpdateView):
    model = SubscriptionTier
    form_class = SubscriptionTierForm
    template_name = "waste_management/tier_form.html"
    success_url = reverse_lazy("waste_management:tier_list")

    def form_valid(self, form):
        messages.success(self.request, "Subscription Tier updated!")
        return super().form_valid(form)


# --- Subscription Sign-Up ---

class SubscribeView(LoginRequiredMixin, View):
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
