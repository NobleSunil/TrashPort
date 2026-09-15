import logging
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from trashport.core.waste_management.models import PickupRequest, Address, WasteCategory

logger = logging.getLogger(__name__)

def _parse_time(time_str):
    """
    Parses a datetime string into a timezone-aware datetime object.
    """
    dt = parse_datetime(str(time_str))
    if not dt:
        try:
            dt = timezone.datetime.fromisoformat(str(time_str).replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Invalid datetime format: {time_str}")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt

def _sync_check_status(user):
    pickups = (
        PickupRequest.objects.filter(citizen=user)
        .select_related("address")
        .exclude(status="CANCELLED")
        .order_by("-schedule_date")
    )
    if not pickups.exists():
        return {"type": "text", "message": "You have no active pickups."}

    lines = []
    for p in pickups:
        time_str = p.schedule_date.strftime("%Y-%m-%d %H:%M") if p.schedule_date else "N/A"
        addr_str = ""
        if getattr(p, "address", None):
            a = p.address
            parts = [a.address_line1]
            if getattr(a, "address_line2", None):
                parts.append(a.address_line2)
            parts.extend([a.city, a.state, a.postal_code])
            addr_str = f" | Address: {', '.join(filter(None, parts))}"
        lines.append(f"- Pickup #{p.display_id}: {time_str} â€” {p.status}{addr_str}")
    return {"type": "text", "message": "Here are your active pickups:\n" + "\n".join(lines)}

def _sync_cancel_pickup(user, pickup_id):
    pickup = (
        PickupRequest.objects.filter(citizen=user)
        .filter(models.Q(user_pickup_number=pickup_id) | models.Q(id=pickup_id))
        .first()
    )
    if not pickup:
        return {"type": "text", "message": "Pickup not found or access denied."}

    # Verify status is PENDING or CONFIRMED (in this DB we match PENDING or active states like ASSIGNED/AWAITING_PAYMENT)
    if pickup.status not in ["PENDING", "CONFIRMED", "AWAITING_PAYMENT", "ASSIGNED"]:
        return {"type": "text", "message": "Only pending or confirmed pickups can be cancelled."}

    pickup.status = "CANCELLED"
    pickup.save(update_fields=["status"])
    return {"type": "action_done", "message": "Your pickup has been cancelled."}

def _sync_edit_pickup(user, pickup_id, new_time_str):
    pickup = (
        PickupRequest.objects.filter(citizen=user)
        .filter(models.Q(user_pickup_number=pickup_id) | models.Q(id=pickup_id))
        .first()
    )
    if not pickup:
        return {"type": "text", "message": "Pickup not found or access denied."}

    new_time = _parse_time(new_time_str)
    pickup.schedule_date = new_time
    pickup.save(update_fields=["schedule_date"])
    return {"type": "action_done", "message": f"Pickup rescheduled to {new_time_str}."}

def _sync_book_pickup(user, address_val=None, scheduled_time_str=None, address_type=None, address_id=None, address_details=None, category_val=None, weight_val=None):
    # Find or create Address instance
    address_obj = None

    if address_type == "new" and address_details:
        address_obj = Address.objects.create(
            user=user,
            address_line1=address_details.get("address_line1"),
            city=address_details.get("city"),
            state=address_details.get("state"),
            postal_code=address_details.get("postal_code"),
            is_default=False
        )
    elif address_type == "saved" and address_id:
        import re
        if str(address_id).isdigit():
            address_obj = Address.objects.filter(id=int(address_id), user=user).first()
        else:
            match = re.search(r'\b\d+\b', str(address_id))
            if match:
                address_obj = Address.objects.filter(id=int(match.group(0)), user=user).first()
            if not address_obj:
                clean_val = str(address_id).split(",")[0].strip()
                address_obj = Address.objects.filter(user=user, address_line1__icontains=clean_val).first()

    # Legacy lookup fallback
    if not address_obj and address_val:
        if str(address_val).isdigit():
            address_obj = Address.objects.filter(id=int(address_val), user=user).first()
        if not address_obj:
            address_obj = Address.objects.filter(user=user, address_line1__icontains=str(address_val)).first()

    # Default fallbacks
    if not address_obj:
        address_obj = Address.objects.filter(user=user, is_default=True).first()
    if not address_obj:
        address_obj = Address.objects.filter(user=user).first()
    if not address_obj:
        address_obj = Address.objects.create(
            user=user,
            address_line1="123 TrashPort Way",
            city="Kochi",
            state="Kerala",
            postal_code="682001",
            is_default=True
        )

    category_obj = None
    if category_val:
        cat_str = str(category_val).strip()
        if cat_str.isdigit():
            category_obj = WasteCategory.objects.filter(id=int(cat_str)).first()
        if not category_obj:
            category_obj = WasteCategory.objects.filter(name__iexact=cat_str).first()
        if not category_obj:
            category_obj = WasteCategory.objects.filter(name__icontains=cat_str).first()
        if not category_obj:
            for word in cat_str.split():
                if len(word) > 2:
                    category_obj = WasteCategory.objects.filter(name__icontains=word).first()
                    if category_obj:
                        break

    if not category_obj:
        category_obj = WasteCategory.objects.first()
    if not category_obj:
        category_obj = WasteCategory.objects.create(
            name="General Waste",
            description="Default waste category",
            fee_per_kg=0.00,
            points_per_kg=0
        )

    # Parse weight_kg
    parsed_weight = Decimal("1.00")
    if weight_val is not None:
        try:
            import re
            weight_match = re.search(r"(\d+(\.\d+)?)", str(weight_val))
            if weight_match:
                val = float(weight_match.group(1))
                if val > 0:
                    parsed_weight = Decimal(f"{val:.2f}")
        except Exception:
            parsed_weight = Decimal("1.00")

    scheduled_time = _parse_time(scheduled_time_str)

    pickup = PickupRequest.objects.create(
        citizen=user,
        address=address_obj,
        category=category_obj,
        weight_kg=parsed_weight,
        schedule_date=scheduled_time,
        status="PENDING"
    )

    # Force status to PENDING if save() logic auto-changes it to AWAITING_PAYMENT
    if pickup.status != "PENDING":
        pickup.status = "PENDING"
        pickup.save(update_fields=["status"])

    return {"type": "action_done", "message": f"Pickup #{pickup.display_id} ({category_obj.name}, {pickup.weight_kg} kg) booked for {scheduled_time_str}!"}

async def execute_action(user, parsed: dict) -> dict:
    """
    Executes a parsed chatbot action in a database-safe async environment.
    """
    try:
        action = parsed.get("action")
        payload = parsed.get("payload", {})

        if action == "check_status":
            return await sync_to_async(_sync_check_status)(user)

        elif action == "cancel_pickup":
            pickup_id = payload.get("pickup_id")
            if not pickup_id:
                return {"type": "text", "message": "Pickup ID is required to cancel a pickup."}
            import re
            match = re.search(r'\d+', str(pickup_id))
            if match:
                pickup_id = int(match.group(0))
            return await sync_to_async(_sync_cancel_pickup)(user, pickup_id)

        elif action == "edit_pickup":
            pickup_id = payload.get("pickup_id")
            new_time = payload.get("new_time")
            if not pickup_id or not new_time:
                return {"type": "text", "message": "Pickup ID and new time are required."}
            import re
            match = re.search(r'\d+', str(pickup_id))
            if match:
                pickup_id = int(match.group(0))
            return await sync_to_async(_sync_edit_pickup)(user, pickup_id, new_time)

        elif action == "book_pickup":
            address = payload.get("address")
            scheduled_time = payload.get("scheduled_time")
            address_type = payload.get("address_type")
            address_id = payload.get("address_id")
            address_details = payload.get("address_details")
            category = payload.get("category") or payload.get("waste_type") or payload.get("type")
            weight = payload.get("weight_kg") or payload.get("weight") or payload.get("estimated_weight")

            if not scheduled_time:
                return {"type": "text", "message": "Scheduled time is required."}

            if not address and not address_type and not address_id and not address_details:
                return {"type": "text", "message": "Address information is required."}

            return await sync_to_async(_sync_book_pickup)(
                user=user,
                address_val=address,
                scheduled_time_str=scheduled_time,
                address_type=address_type,
                address_id=address_id,
                address_details=address_details,
                category_val=category,
                weight_val=weight,
            )

        else:
            return {"type": "text", "message": "Could not complete that action. Please try again."}

    except Exception as e:
        logger.error(f"Action Execution Error: {e}", exc_info=True)
        return {"type": "text", "message": "Could not complete that action. Please try again."}
