from datetime import timedelta
from django import forms
from django.utils import timezone
from waste_management.models import Address, PickupRequest, Complaint


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["address_line1", "address_line2", "city", "state", "postal_code", "latitude", "longitude", "is_default"]
        widgets = {
            "address_line1": forms.TextInput(attrs={"class": "form-control", "id": "id_address_line1", "placeholder": "e.g., 42 MG Road, Indiranagar"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control", "id": "id_address_line2", "placeholder": "Apartment, suite, unit etc. (Optional)"}),
            "city": forms.TextInput(attrs={"class": "form-control", "id": "id_city", "placeholder": "e.g., Bengaluru / Kochi"}),
            "state": forms.TextInput(attrs={"class": "form-control", "id": "id_state", "placeholder": "e.g., Karnataka / Kerala"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control", "id": "id_postal_code", "placeholder": "e.g., 560038 / 682001"}),
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_is_default"}),
        }


class PickupRequestForm(forms.ModelForm):
    new_address_line1 = forms.CharField(
        required=False,
        label="Pickup Street Address",
        widget=forms.TextInput(attrs={"class": "form-control", "id": "id_new_address_line1", "placeholder": "Enter street address (e.g. 42 MG Road, Indiranagar)"})
    )
    new_city = forms.CharField(
        required=False,
        label="City",
        widget=forms.TextInput(attrs={"class": "form-control", "id": "id_new_city", "placeholder": "Kochi / Bangalore"})
    )
    new_postal_code = forms.CharField(
        required=False,
        label="Postal Code",
        widget=forms.TextInput(attrs={"class": "form-control", "id": "id_new_postal_code", "placeholder": "560038 / 682001"})
    )

    class Meta:
        model = PickupRequest
        fields = ["address", "category", "weight_kg", "quantity_estimate", "schedule_date", "latitude", "longitude"]
        widgets = {
            "address": forms.Select(attrs={"class": "form-select", "id": "id_address"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "Estimated weight in kg"}),
            "quantity_estimate": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 2 bags, 3 boxes (optional)"}),
            "schedule_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["address"].required = False
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

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get("address")
        new_address_line1 = cleaned_data.get("new_address_line1")

        if not address and not new_address_line1:
            raise forms.ValidationError("Please select a saved address or enter a pickup street address.")
        return cleaned_data

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
