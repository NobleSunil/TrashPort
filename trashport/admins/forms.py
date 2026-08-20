from django import forms
from django.contrib.auth import get_user_model

from waste_management.models import SubscriptionTier, WasteCategory

User = get_user_model()


class WasteCategoryForm(forms.ModelForm):
    class Meta:
        model = WasteCategory
        fields = ["name", "description", "fee_per_kg", "points_per_kg"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}),
            "fee_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.00"}),
            "points_per_kg": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class SubscriptionTierForm(forms.ModelForm):
    class Meta:
        model = SubscriptionTier
        fields = ["name", "price", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tier Name"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CollectorCreationForm(forms.ModelForm):
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
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
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

