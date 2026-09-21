from datetime import timedelta
from django import forms
from django.utils import timezone
from trashport.core.waste_management.models import Address, PickupRequest, Complaint, WasteCategory


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

    city = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Select City...",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_city_select"})
    )

    class Meta:
        model = PickupRequest
        fields = ["city", "address", "category", "weight_kg", "quantity_estimate", "schedule_date", "latitude", "longitude"]
        widgets = {
            "city": forms.Select(attrs={"class": "form-select", "id": "id_city_select"}),
            "address": forms.Select(attrs={"class": "form-select", "id": "id_address"}),
            "category": forms.Select(attrs={"class": "form-select", "id": "id_category"}),
            "weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "max": "100.00", "placeholder": "Estimated weight in kg (Max 100 kg)"}),
            "quantity_estimate": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 2 boxes, 3 packages (optional)"}),
            "schedule_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if "quantity_estimate" in self.fields:
            self.fields["quantity_estimate"].label = "Number of Package Boxes"
        self.fields["address"].required = False
        from trashport.core.waste_management.models import City
        self.fields["city"].queryset = City.objects.filter(is_active=True).order_by("name")
        self.fields["city"].required = False

        if user:
            # Only display addresses belonging to the logged-in citizen
            self.fields["address"].queryset = Address.objects.filter(user=user, is_hidden=False)

        if "category" in self.fields:
            self.fields["category"].queryset = WasteCategory.objects.all().order_by("name")
            self.fields["category"].label_from_instance = lambda obj: obj.name
            self.fields["category"].empty_label = "Select Waste Category..."

        # Enforce minimum schedule date: at least 3 hours from current time
        now_local = timezone.localtime(timezone.now())
        earliest_allowed = now_local + timedelta(hours=3)

        # If earliest_allowed is before 7:00 AM today, clamp to 7:00 AM today
        day_start = earliest_allowed.replace(hour=7, minute=0, second=0, microsecond=0)
        day_end = earliest_allowed.replace(hour=20, minute=30, second=0, microsecond=0)

        if earliest_allowed < day_start:
            default_target = day_start
        elif earliest_allowed > day_end:
            # After 8:30 PM today, roll over to tomorrow 7:00 AM
            default_target = (earliest_allowed + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        else:
            default_target = earliest_allowed

        min_datetime_str = earliest_allowed.strftime("%Y-%m-%dT%H:%M")
        self.fields["schedule_date"].widget.attrs["min"] = min_datetime_str
        self.fields["schedule_date"].help_text = (
            "Pickups can be booked between 7:00 AM and 8:30 PM, at least 3 hours in advance."
        )
        if not self.initial.get("schedule_date"):
            self.initial["schedule_date"] = default_target.strftime("%Y-%m-%dT%H:%M")

    def clean_weight_kg(self):
        from decimal import Decimal
        weight_kg = self.cleaned_data.get("weight_kg")
        if weight_kg is not None:
            if weight_kg <= Decimal("0"):
                raise forms.ValidationError("Weight must be greater than 0 kg.")
            if weight_kg > Decimal("100.00"):
                raise forms.ValidationError("Maximum pickup weight limit for users is 100 kg per request.")
        return weight_kg

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get("address")
        new_address_line1 = cleaned_data.get("new_address_line1")
        new_city_name = cleaned_data.get("new_city")
        selected_city = cleaned_data.get("city")
        category = cleaned_data.get("category")
        weight_kg = cleaned_data.get("weight_kg")
        lat = cleaned_data.get("latitude")
        lng = cleaned_data.get("longitude")

        if not address and not new_address_line1:
            raise forms.ValidationError("Please select a saved address or enter a pickup street address.")

        if category and weight_kg:
            allowed_max = getattr(category, "max_weight_kg", None)
            if allowed_max is not None and weight_kg > allowed_max:
                self.add_error(
                    "weight_kg",
                    f"Maximum weight limit for {category.name} is {allowed_max} kg. You entered {weight_kg} kg."
                )

        # Resolve City entity
        from trashport.core.waste_management.models import City
        target_city = selected_city
        if not target_city and address:
            if address.city_ref:
                target_city = address.city_ref
            elif address.city:
                target_city = City.objects.filter(name__iexact=address.city.strip()).first()
        if not target_city and new_city_name:
            target_city = City.objects.filter(name__iexact=new_city_name.strip()).first()

        # Fallback to first active city (e.g. Kochi) if not explicitly matched
        if not target_city:
            target_city = City.objects.filter(is_active=True).first()

        # Determine effective coordinates for distance check
        effective_lat = float(lat) if lat is not None else (float(address.latitude) if address and address.latitude is not None else 9.9312)
        effective_lng = float(lng) if lng is not None else (float(address.longitude) if address and address.longitude is not None else 76.2673)

        # Validate city, active hub, registered collectors, and 20 km radius via RouteService
        if target_city:
            from trashport.core.waste_management.services import RouteService
            try:
                _, hub, dist = RouteService.validate_pickup_eligibility(target_city, effective_lat, effective_lng)
                cleaned_data["validated_city"] = target_city
                cleaned_data["validated_hub"] = hub
                cleaned_data["validated_distance_km"] = dist
            except forms.ValidationError as e:
                raise e
            except Exception as exc:
                raise forms.ValidationError(str(exc))

        return cleaned_data

    def clean_schedule_date(self):
        schedule_date = self.cleaned_data.get("schedule_date")
        if schedule_date:
            local_schedule = timezone.localtime(schedule_date)
            now_local = timezone.localtime(timezone.now())
            min_allowed_time = now_local + timedelta(hours=3)

            # 1. Check at least 3 hours in advance
            if local_schedule < min_allowed_time:
                diff = min_allowed_time - local_schedule
                hours_diff = diff.total_seconds() / 3600
                raise forms.ValidationError(
                    f"Pickups must be scheduled at least 3 hours in advance from now. "
                    f"Earliest available slot is after {min_allowed_time.strftime('%b %d, %Y at %I:%M %p')}."
                )

            # 2. Check operating window: 7:00 AM (07:00) to 8:30 PM (20:30)
            slot_time = local_schedule.time()
            from datetime import time
            morning_start = time(7, 0)
            evening_end = time(20, 30)

            if slot_time < morning_start or slot_time > evening_end:
                raise forms.ValidationError(
                    f"Pickup collections operate only between 7:00 AM and 8:30 PM. "
                    f"Selected time is {slot_time.strftime('%I:%M %p')}. Please choose a time between 7:00 AM and 8:30 PM."
                )

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


from trashport.core.waste_management.models import AnonymousFeedback

class AnonymousFeedbackForm(forms.ModelForm):
    """Form for citizens and visitors to submit anonymous feedback directly to administrators."""
    class Meta:
        model = AnonymousFeedback
        fields = ["category", "subject", "message"]
        widgets = {
            "category": forms.Select(attrs={
                "class": "form-select border-0 bg-white/10 text-white rounded-xl py-3 px-4 focus:ring-2 focus:ring-brand-500",
                "id": "anonFeedbackCategory"
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-control border-0 bg-white/10 text-white rounded-xl py-3 px-4 placeholder-gray-400 focus:ring-2 focus:ring-brand-500",
                "placeholder": "Subject / Summary (e.g. Missed collection in Sector 4, App suggestion...)",
                "id": "anonFeedbackSubject"
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control border-0 bg-white/10 text-white rounded-xl py-3 px-4 placeholder-gray-400 focus:ring-2 focus:ring-brand-500",
                "rows": 3,
                "placeholder": "Write your honest feedback, report, or idea here... No personal details required.",
                "id": "anonFeedbackMessage"
            }),
        }

