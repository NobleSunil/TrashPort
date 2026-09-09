from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, RedirectView, UpdateView

from .models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    """
    Renders detail page for a user profile.
    """
    model = User

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_detail_view = UserDetailView.as_view()


from django.contrib.auth import update_session_auth_hash
from .forms import UserProfileUpdateForm


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Allows a user to update profile details (name, email, phone_number, and set/change password).
    """
    model = User
    form_class = UserProfileUpdateForm
    success_message = _("Profile details successfully updated.")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Keep user logged in if password was changed
        if form.cleaned_data.get("new_password"):
            update_session_auth_hash(self.request, self.object)
            messages.info(self.request, _("Password updated successfully."))
        return response

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirects user to their own profile page.
    """
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail")


user_redirect_view = UserRedirectView.as_view()


class UserDeleteView(LoginRequiredMixin, DeleteView):
    """
    Allows a user to delete their account.
    """
    model = User
    template_name = "users/user_confirm_delete.html"
    success_url = reverse_lazy("home")

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted successfully.")
        return redirect(self.success_url)


user_delete_view = UserDeleteView.as_view()
