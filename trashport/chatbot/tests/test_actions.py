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
