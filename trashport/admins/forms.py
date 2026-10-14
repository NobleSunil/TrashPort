"""
Admin and Operations Forms.

Defines form structures for administrators to:
- Configure Waste Categories (pricing per kg and green reward points).
- Register verified waste collector accounts directly with encrypted credentials.
"""

from django import forms
from django.contrib.auth import get_user_model

from trashport.core.waste_management.models import WasteCategory

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


from trashport.core.waste_management.models import CollectorPayoutSetting

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


from trashport.core.waste_management.models import City, Hub, Vehicle, Route, RoutePickup, PickupRequest


class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ["name", "state", "is_active"]
        labels = {
            "name": "City / Grama Panchayath Name",
            "state": "State",
            "is_active": "Operational Status",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kochi / Kumarakom Grama Panchayat"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kerala"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class HubForm(forms.ModelForm):
    """
    Form for registering or updating Hub infrastructure facilities.
    Supports dual entry modes for city assignment:
      1. Dropdown Selection: Choose from pre-existing active City/Panchayath records.
      2. Manual Entry: Directly type a new or unlisted City/Panchayath, which is
         automatically resolved, created, and linked to the Hub.
    """
    city_entry_mode = forms.ChoiceField(
        choices=[("select", "Choose from List"), ("manual", "Manual Entry")],
        required=False,
        initial="select",
        widget=forms.HiddenInput(attrs={"id": "id_city_entry_mode"}),
    )
    manual_city = forms.CharField(
        required=False,
        label="Manual City / Panchayath Entry",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Adimali Grama Panchayat, Kerala",
            "id": "id_manual_city",
        }),
        help_text="Type city/panchayath name manually if not in the dropdown list."
    )

    class Meta:
        model = Hub
        fields = ["name", "city", "city_entry_mode", "manual_city", "latitude", "longitude", "address", "is_active"]
        labels = {
            "name": "Hub / Facility Name",
            "city": "Assigned City / Panchayath",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "address": "Physical Address / Landmark",
            "is_active": "Active Hub",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kumarakom Panchayath Hub"}),
            "city": forms.Select(attrs={"class": "form-select", "id": "id_city_select"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "9.931200"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "76.267300"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Street Address / Landmark"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # City dropdown is optional at field-level so manual_city can satisfy the requirement
        self.fields["city"].required = False

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get("city_entry_mode") or "select"
        city = cleaned_data.get("city")
        manual_city = (cleaned_data.get("manual_city") or "").strip()

        # If manual mode is active or manual_city text was supplied
        if mode == "manual" or (manual_city and not city):
            if not manual_city:
                self.add_error("manual_city", "Please enter the City or Panchayath name.")
                return cleaned_data

            # Parse out city name and optional state (e.g. "Adimali Grama Panchayat, Kerala")
            parts = [p.strip() for p in manual_city.split(",") if p.strip()]
            city_name = parts[0] if parts else manual_city
            state_name = parts[1] if len(parts) > 1 else "Kerala"

            # Case-insensitive lookup or auto-creation of City record
            city_obj = City.objects.filter(name__iexact=city_name).first()
            if not city_obj:
                city_obj = City.objects.create(
                    name=city_name,
                    state=state_name,
                    is_active=True,
                )
            cleaned_data["city"] = city_obj

        else:
            # Mode is "select": ensure city was chosen, or fall back to manual_city
            if not city:
                if manual_city:
                    parts = [p.strip() for p in manual_city.split(",") if p.strip()]
                    city_name = parts[0] if parts else manual_city
                    state_name = parts[1] if len(parts) > 1 else "Kerala"
                    city_obj = City.objects.filter(name__iexact=city_name).first()
                    if not city_obj:
                        city_obj = City.objects.create(
                            name=city_name,
                            state=state_name,
                            is_active=True,
                        )
                    cleaned_data["city"] = city_obj
                else:
                    self.add_error("city", "This field is required. Please select or manually enter a City / Panchayath.")

        return cleaned_data


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["vehicle_number", "hub", "driver", "max_capacity", "status"]
        widgets = {
            "vehicle_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. KL-07-TP-1001"}),
            "hub": forms.Select(attrs={"class": "form-select"}),
            "driver": forms.Select(attrs={"class": "form-select"}),
            "max_capacity": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "50", "placeholder": "5"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit drivers to active collectors
        self.fields["driver"].queryset = User.objects.filter(role=User.Roles.COLLECTOR, is_active=True)
        self.fields["driver"].required = False


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ["vehicle", "hub", "start_time", "status"]
        widgets = {
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "hub": forms.Select(attrs={"class": "form-select"}),
            "start_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }



