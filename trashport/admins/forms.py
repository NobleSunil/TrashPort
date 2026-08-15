from django import forms
from waste_management.models import WasteCategory, SubscriptionTier


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
