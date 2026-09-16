# ==============================================================================
# TrashPort - User Account Management Views
# ==============================================================================
# This module provides class-based views for user profile operations:
# - Viewing profile details
# - Updating user information and passwords
# - Redirecting to the user's profile
# - Account deletion
# ==============================================================================

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from .forms import UserProfileUpdateForm
from .models import User


# ==============================================================================
# 1. User Detail View
# ==============================================================================
class UserDetailView(LoginRequiredMixin, DetailView):
    """
    Renders detail page for the currently logged-in user profile.
    Requires the user to be authenticated.
    """
    model = User

    def get_object(self, queryset: QuerySet | None = None) -> User:
        # Guarantee that only authenticated users access their own object
        assert self.request.user.is_authenticated  # type guard
        # Return the currently logged-in user instance
        return self.request.user


# Export standard view callable for URL routing
user_detail_view = UserDetailView.as_view()


# ==============================================================================
# 2. User Profile Update View
# ==============================================================================
class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Allows an authenticated user to update profile details:
    - Name, Email, Phone Number
    - Optional password change/setup
    """
    model = User
    form_class = UserProfileUpdateForm
    success_message = _("Profile details successfully updated.")

    def form_valid(self, form):
        # Save the valid form data via the parent UpdateView
        response = super().form_valid(form)

        # If user changed or set a new password, update session auth hash
        # This prevents Django from logging the user out upon password change
        if form.cleaned_data.get("new_password"):
            update_session_auth_hash(self.request, self.object)
            messages.info(self.request, _("Password updated successfully."))

        return response

    def get_success_url(self) -> str:
        # Redirect back to the user detail page after a successful update
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        # Ensure updates are applied only to the requesting user
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


# Export standard view callable for URL routing
user_update_view = UserUpdateView.as_view()


# ==============================================================================
# 3. User Profile Redirect View
# ==============================================================================
class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirects an authenticated user directly to their own profile page.
    Used for clean navigation shortcuts (e.g., /users/~redirect/).
    """
    permanent = False

    def get_redirect_url(self) -> str:
        # Return the reverse URL for user profile detail
        return reverse("users:detail")


# Export standard view callable for URL routing
user_redirect_view = UserRedirectView.as_view()


# ==============================================================================
# 4. User Account Delete View
# ==============================================================================
class UserDeleteView(LoginRequiredMixin, DeleteView):
    """
    Allows an authenticated user to permanently delete their account.
    Logs out the user session before removing the record to prevent session orphans.
    """
    model = User
    template_name = "users/user_confirm_delete.html"
    success_url = reverse_lazy("home")

    def get_object(self, queryset: QuerySet | None = None) -> User:
        # Ensure the user can only delete their own account
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

    def delete(self, request, *args, **kwargs):
        # Retrieve the user object to delete
        user = self.get_object()
        # Log out the user before deletion so the session is cleanly closed
        logout(request)
        # Delete user record and all associated cascade records
        user.delete()
        # Provide user feedback message
        messages.success(request, "Your account has been deleted successfully.")
        # Redirect to the home landing page
        return redirect(self.success_url)


# Export standard view callable for URL routing
user_delete_view = UserDeleteView.as_view()
