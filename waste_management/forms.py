from django import forms
from .models import Address, PickupRequest, Complaint, WasteCategory

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["address_line1", "address_line2", "city", "state", "postal_code", "is_default"]
        widgets = {
            "address_line1": forms.TextInput(attrs={"class": "form-control", "placeholder": "123 Main St"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apartment, suite, unit etc."}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Kochi"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "Kerala"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "682001"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PickupRequestForm(forms.ModelForm):
    class Meta:
        model = PickupRequest
        fields = ["address", "category", "quantity_estimate", "schedule_date"]
        widgets = {
            "address": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity_estimate": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 2 bags, 5kg"}),
            "schedule_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Only display addresses belonging to the logged-in citizen
            self.fields["address"].queryset = Address.objects.filter(user=user)


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["pickup_request", "title", "description"]
        widgets = {
            "pickup_request": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Brief title of issue"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Provide details of your complaint..."}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Only display pickup requests belonging to this citizen
            self.fields["pickup_request"].queryset = PickupRequest.objects.filter(citizen=user)


class WasteCategoryForm(forms.ModelForm):
    class Meta:
        model = WasteCategory
        fields = ["name", "price_per_kg", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category Name"}),
            "price_per_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "e.g. 0.50"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}),
        }
