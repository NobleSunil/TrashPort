from datetime import timedelta
from django import forms
from django.utils import timezone
from waste_management.models import Address, PickupRequest, Complaint


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
        fields = ["address", "category", "weight_kg", "quantity_estimate", "schedule_date"]
        widgets = {
            "address": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "Estimated weight in kg"}),
            "quantity_estimate": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 2 bags, 3 boxes (optional)"}),
            "schedule_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Only display addresses belonging to the logged-in citizen
            self.fields["address"].queryset = Address.objects.filter(user=user)

        # Enforce minimum schedule date: at least 3 hours from current time
        min_datetime = timezone.localtime(timezone.now() + timedelta(hours=3))
        min_datetime_str = min_datetime.strftime("%Y-%m-%dT%H:%M")
        self.fields["schedule_date"].widget.attrs["min"] = min_datetime_str
        self.fields["schedule_date"].help_text = "Pickups must be scheduled at least 3 hours in advance."
        if not self.initial.get("schedule_date"):
            self.initial["schedule_date"] = min_datetime_str

    def clean_schedule_date(self):
        schedule_date = self.cleaned_data.get("schedule_date")
        if schedule_date:
            min_allowed_time = timezone.now() + timedelta(hours=3)
            if schedule_date < min_allowed_time:
                raise forms.ValidationError("Pickup must be scheduled at least 3 hours in advance from the current time.")
        return schedule_date


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

