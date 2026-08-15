from django import forms
from waste_management.models import WasteCategory


class WasteCategoryForm(forms.ModelForm):
    class Meta:
        model = WasteCategory
        fields = ["name", "price_per_kg", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
            "price_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "e.g. 0.50"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}),
        }
