import logging
from asgiref.sync import sync_to_async
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from waste_management.models import PickupRequest, Address, WasteCategory

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
    pickups = PickupRequest.objects.filter(citizen=user).exclude(status="CANCELLED").order_by("-schedule_date")
    if not pickups.exists():
        return {"type": "text", "message": "You have no active pickups."}

    lines = []
    for p in pickups:
        time_str = p.schedule_date.strftime("%Y-%m-%d %H:%M") if p.schedule_date else "N/A"
        lines.append(f"{time_str} — {p.status}")
    return {"type": "text", "message": "Here are your active pickups:\n" + "\n".join(lines)}

def _sync_cancel_pickup(user, pickup_id):
    pickup = PickupRequest.objects.filter(id=pickup_id, citizen=user).first()
    if not pickup:
        return {"type": "text", "message": "Pickup not found or access denied."}

    # Verify status is PENDING or CONFIRMED (in this DB we match PENDING or active states like ASSIGNED/AWAITING_PAYMENT)
    if pickup.status not in ["PENDING", "CONFIRMED", "AWAITING_PAYMENT", "ASSIGNED"]:
        return {"type": "text", "message": "Only pending or confirmed pickups can be cancelled."}

    pickup.status = "CANCELLED"
    pickup.save(update_fields=["status"])
    return {"type": "action_done", "message": "Your pickup has been cancelled."}

def _sync_edit_pickup(user, pickup_id, new_time_str):
    pickup = PickupRequest.objects.filter(id=pickup_id, citizen=user).first()
    if not pickup:
        return {"type": "text", "message": "Pickup not found or access denied."}

    new_time = _parse_time(new_time_str)
    pickup.schedule_date = new_time
    pickup.save(update_fields=["schedule_date"])
    return {"type": "action_done", "message": f"Pickup rescheduled to {new_time_str}."}

def _sync_book_pickup(user, address_val=None, scheduled_time_str=None, address_type=None, address_id=None, address_details=None):
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
        address_obj = Address.objects.filter(id=int(address_id), user=user).first()
    
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

    category_obj = WasteCategory.objects.first()
    if not category_obj:
        category_obj = WasteCategory.objects.create(
            name="General Waste",
            description="Default waste category",
            fee_per_kg=0.00,
            points_per_kg=0
        )

    scheduled_time = _parse_time(scheduled_time_str)

    pickup = PickupRequest.objects.create(
        citizen=user,
        address=address_obj,
        category=category_obj,
        schedule_date=scheduled_time,
        status="PENDING"
    )

    # Force status to PENDING if save() logic auto-changes it to AWAITING_PAYMENT
    if pickup.status != "PENDING":
        pickup.status = "PENDING"
        pickup.save(update_fields=["status"])

    return {"type": "action_done", "message": f"Pickup booked for {scheduled_time_str}!"}

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
            return await sync_to_async(_sync_cancel_pickup)(user, pickup_id)

        elif action == "edit_pickup":
            pickup_id = payload.get("pickup_id")
            new_time = payload.get("new_time")
            if not pickup_id or not new_time:
                return {"type": "text", "message": "Pickup ID and new time are required."}
            return await sync_to_async(_sync_edit_pickup)(user, pickup_id, new_time)

        elif action == "book_pickup":
            address = payload.get("address")
            scheduled_time = payload.get("scheduled_time")
            address_type = payload.get("address_type")
            address_id = payload.get("address_id")
            address_details = payload.get("address_details")
            
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
                address_details=address_details
            )

        else:
            return {"type": "text", "message": "Could not complete that action. Please try again."}

    except Exception as e:
        logger.error(f"Action Execution Error: {e}", exc_info=True)
        return {"type": "text", "message": "Could not complete that action. Please try again."}
