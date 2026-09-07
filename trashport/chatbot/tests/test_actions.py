import pytest
from django.contrib.auth import get_user_model
from trashport.chatbot.actions.schedule_pickup import SchedulePickupAction
from trashport.chatbot.actions.check_payment import CheckPaymentAction
from trashport.chatbot.services.response_builder import ChatResponseBuilder

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestChatActions:
    def test_schedule_pickup_action(self):
        action = SchedulePickupAction()
        res = action.execute(user=None, text="book pickup", slots={"category": "E-waste"})
        assert "E-waste" in res["reply"]
        assert res["action"] == "NAVIGATE"

    def test_check_payment_action(self):
        user = User.objects.create_user(email="actionuser@trashport.local", name="Action User")
        user.wallet_points = 250
        user.save()

        action = CheckPaymentAction()
        res = action.execute(user=user, text="check points", slots={})
        assert "250" in res["reply"]
        assert res["points"] == 250

    def test_full_response_builder(self):
        user = User.objects.create_user(email="builderuser@trashport.local", name="Builder User")
        res = ChatResponseBuilder.process_user_message("Hello, how to recycle dry waste?", user=user)
        assert "session_key" in res
        assert "reply" in res
        assert len(res["reply"]) > 0

    def test_system_prompt_full_address(self):
        from waste_management.models import Address, PickupRequest, WasteCategory
        from trashport.chatbot.system_prompt import build_system_prompt
        from django.utils import timezone

        user = User.objects.create_user(email="addressuser@trashport.local", name="Address User")
        addr = Address.objects.create(
            user=user,
            address_line1="42 Green Street",
            address_line2="Apt 3B",
            city="Ernakulam",
            state="Kerala",
            postal_code="682001",
            is_default=True
        )
        cat = WasteCategory.objects.create(name="Plastic", fee_per_kg=5.0)
        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            schedule_date=timezone.now(),
            status="PENDING"
        )
        prompt = build_system_prompt(user, [pickup])
        assert "42 Green Street" in prompt
        assert "Apt 3B" in prompt
        assert "Ernakulam" in prompt
        assert "682001" in prompt
        assert f"- ID: {pickup.display_id}" in prompt
        assert "Plastic" in prompt

    def test_sync_check_status_includes_full_address_and_id(self):
        from waste_management.models import Address, PickupRequest, WasteCategory
        from trashport.chatbot.services.action_handler import _sync_check_status
        from django.utils import timezone

        user = User.objects.create_user(email="statususer@trashport.local", name="Status User")
        addr = Address.objects.create(
            user=user,
            address_line1="10 Downing Court",
            address_line2="Floor 2",
            city="Kochi",
            state="Kerala",
            postal_code="682016",
            is_default=True
        )
        cat = WasteCategory.objects.create(name="Dry Waste", fee_per_kg=2.0)
        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            schedule_date=timezone.now(),
            status="ASSIGNED"
        )
        pickup.refresh_from_db()
        res = _sync_check_status(user)
        assert res["type"] == "text"
        assert f"Pickup #{pickup.display_id}" in res["message"]
        assert "10 Downing Court" in res["message"]
        assert "Floor 2" in res["message"]
        assert pickup.status in res["message"]

    def test_sync_book_pickup_with_waste_category(self):
        from waste_management.models import Address, PickupRequest, WasteCategory
        from trashport.chatbot.services.action_handler import _sync_book_pickup

        user = User.objects.create_user(email="bookinguser@trashport.local", name="Booking User")
        addr = Address.objects.create(
            user=user,
            address_line1="15 Lake View Rd",
            city="Kochi",
            state="Kerala",
            postal_code="682020",
            is_default=True
        )
        cat = WasteCategory.objects.create(name="Electronic Waste", fee_per_kg=15.0)

        res = _sync_book_pickup(
            user=user,
            address_type="saved",
            address_id=addr.id,
            scheduled_time_str="2026-09-15 14:00",
            category_val="Electronic Waste",
            weight_val="4.5 kg"
        )
        assert res["type"] == "action_done"
        assert "Electronic Waste" in res["message"]
        assert "4.50 kg" in res["message"]

        created_pickup = PickupRequest.objects.filter(citizen=user).first()
        assert created_pickup is not None
        assert created_pickup.category.name == "Electronic Waste"
        assert float(created_pickup.weight_kg) == 4.50
        assert created_pickup.user_pickup_number == 1
        assert created_pickup.display_id == 1
