"""
Admin and Operations Forms.

Defines form structures for administrators to:
- Configure Waste Categories (pricing per kg and green reward points).
- Register verified waste collector accounts directly with encrypted credentials.
"""

from django import forms
from django.contrib.auth import get_user_model

from waste_management.models import WasteCategory

User = get_user_model()


class WasteCategoryForm(forms.ModelForm):
    """Form for creating and editing waste categories and their pricing rules."""
    class Meta:
        model = WasteCategory
        fields = ["name", "description", "fee_per_kg", "points_per_kg", "max_weight_kg"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}),
            "fee_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.00"}),
            "points_per_kg": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "max_weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "Maximum allowed weight in kg (e.g. 100)"}),
        }


class CollectorCreationForm(forms.ModelForm):
    """Administrative form to directly provision and onboard a collector user account."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}))

    class Meta:
        model = User
        fields = ["email", "name"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "collector@trashport.org"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
        }

    def clean(self):
        """Validates that password and confirm_password match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        """Hashes password and sets the user role to COLLECTOR upon creation."""
        user = super().save(commit=False)
        user.role = User.Roles.COLLECTOR
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user



class WalletPointAdjustmentForm(forms.Form):
    points = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 50 or -20"}),
        help_text="Positive number to award points, negative to deduct points."
    )
    reason = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Reason for adjustment"}),
        required=False
    )


from waste_management.models import CollectorPayoutSetting

class CollectorPayoutSettingForm(forms.ModelForm):
    """Form for admins to configure collector payout rates and commissions."""
    class Meta:
        model = CollectorPayoutSetting
        fields = ["base_min_payout", "rate_per_km", "extra_weight_commission_percent"]
        widgets = {
            "base_min_payout": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.00", "placeholder": "e.g. 25.00"}),
            "rate_per_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.00", "placeholder": "e.g. 2.00"}),
            "extra_weight_commission_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.00", "max": "100.00", "placeholder": "e.g. 20.00"}),
        }
        labels = {
            "base_min_payout": "Minimum Base Payout (Rs.)",
            "rate_per_km": "Rate per Kilometer (Rs./km)",
            "extra_weight_commission_percent": "Extra Weight Commission (%)",
        }
        help_texts = {
            "base_min_payout": "Minimum guaranteed payment to the collector for every completed pickup job.",
            "rate_per_km": "Additional compensation paid per kilometer of pickup travel distance.",
            "extra_weight_commission_percent": "Percentage share given to collector from excess weight penalty fees.",
        }


