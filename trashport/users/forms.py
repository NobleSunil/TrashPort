# ==============================================================================
# TrashPort - User Account Forms
# ==============================================================================
# This module defines Django and django-allauth forms used for:
# - Admin user creation and change
# - Public registration (Signup) with role selection (Citizen / Collector)
# - Profile updates (name, phone, email, and password setup)
# ==============================================================================

import re

from allauth.account.adapter import get_adapter
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User


# ==============================================================================
# 1. Django Admin User Management Forms
# ==============================================================================
class UserAdminChangeForm(admin_forms.UserChangeForm):
    """
    Form used within Django admin to modify existing User records.
    Maps email as the primary credential field.
    """
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form used within Django admin to create brand new User records.
    Enforces unique email validation.
    """
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


# ==============================================================================
# 2. Public User Registration Form (Allauth Signup)
# ==============================================================================
class UserSignupForm(SignupForm):
    """
    Extended django-allauth signup form.
    Captures:
    - User's full name
    - Selected platform role (Citizen or Collector)
    - Operating Hub / Panchayath (required for Collectors)
    """
    role = forms.ChoiceField(
        choices=[("CITIZEN", "Citizen"), ("COLLECTOR", "Collector")],
        required=True,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_role"})
    )
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"})
    )
    hub = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Select your Operating Hub / Panchayath",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_hub"}),
        help_text=_("Collection Hub to which this collector is assigned"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from trashport.core.waste_management.models import Hub
        self.fields["hub"].queryset = Hub.objects.filter(is_active=True).select_related("city").order_by("city__name", "name")

    def clean_name(self):
        # Validate that the full name only contains alphabetical characters and whitespace
        name = self.cleaned_data.get("name")
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError("Name must contain only letters and spaces.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        hub = cleaned_data.get("hub")
        if role == "COLLECTOR" and not hub:
            self.add_error("hub", "Collectors must specify their operating Hub / Panchayath.")
        return cleaned_data

    def save(self, request):
        # Delegate user object creation to allauth adapter
        adapter = get_adapter(request)
        user = adapter.new_user(request)
        # Assign custom registration fields before saving
        user.role = self.cleaned_data["role"]
        user.name = self.cleaned_data["name"]
        if self.cleaned_data.get("hub"):
            user.hub = self.cleaned_data["hub"]
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        return user


# ==============================================================================
# 3. Social Account Signup Form
# ==============================================================================
class UserSocialSignupForm(SocialSignupForm):
    """
    Form rendered when a user signs up using third-party social accounts (e.g. Google OAuth).
    """


# ==============================================================================
# 4. User Profile & Password Update Form
# ==============================================================================
class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for authenticated users to update their profile:
    - Name, Email, Phone Number
    - Optional password change or initial setup (for Google OAuth users)
    """
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter new password"}),
        required=False,
        label=_("New Password (leave blank to keep current password)"),
        help_text=_("At least 8 characters if changing or setting for the first time."),
    )

    class Meta:
        model = User
        fields = ["name", "email", "phone_number"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "+91 9876543210"}),
        }

    def clean_name(self):
        # Ensure user name contains valid text characters
        name = self.cleaned_data.get("name")
        if name and not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError(_("Name must contain only letters and spaces."))
        return name

    def clean_phone_number(self):
        # Validate format of contact phone number (optional, but must be 7-15 digits if provided)
        phone = self.cleaned_data.get("phone_number")
        if phone:
            phone_stripped = phone.strip()
            if not re.match(r'^\+?[0-9\s\-]{7,15}$', phone_stripped):
                raise forms.ValidationError(_("Enter a valid phone number (7 to 15 digits)."))
            return phone_stripped
        return phone

    def clean_email(self):
        # Validate unique email address (excluding the current user's own record)
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("This email is already in use by another account."))
        return email

    def clean_new_password(self):
        # Validate minimum password length constraint if a new password was supplied
        password = self.cleaned_data.get("new_password")
        if password and len(password) < 8:
            raise forms.ValidationError(_("Password must be at least 8 characters long."))
        return password

    def save(self, commit=True):
        # Update model fields without immediate commit to permit password hashing
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            # Hash password securely using Django's PBKDF2 / Argon2 algorithm
            user.set_password(new_password)
        if commit:
            user.save()
        return user

