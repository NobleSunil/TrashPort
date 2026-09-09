import re
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    """
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


from allauth.account.adapter import get_adapter

class UserSignupForm(SignupForm):
    """
    Form rendered on user sign up section.
    """
    role = forms.ChoiceField(
        choices=[("CITIZEN", "Citizen"), ("COLLECTOR", "Collector")],
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"})
    )

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError("Name must contain only letters and spaces.")
        return name

    def save(self, request):
        adapter = get_adapter(request)
        user = adapter.new_user(request)
        user.role = self.cleaned_data["role"]
        user.name = self.cleaned_data["name"]
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        return user


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user signs up using social accounts.
    """
