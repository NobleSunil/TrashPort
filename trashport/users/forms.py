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


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for updating User profile: name, email, phone_number, and set/change password.
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
        name = self.cleaned_data.get("name")
        if name and not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError(_("Name must contain only letters and spaces."))
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if phone:
            phone_stripped = phone.strip()
            if not re.match(r'^\+?[0-9\s\-]{7,15}$', phone_stripped):
                raise forms.ValidationError(_("Enter a valid phone number (7 to 15 digits)."))
            return phone_stripped
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("This email is already in use by another account."))
        return email

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password and len(password) < 8:
            raise forms.ValidationError(_("Password must be at least 8 characters long."))
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user

