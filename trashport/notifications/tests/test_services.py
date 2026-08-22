import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from trashport.notifications.models import Notification
from trashport.notifications.services import NotificationService

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestNotificationService:
    def test_create_notification(self):
        user = User.objects.create_user(email="notifuser@trashport.local", name="Notif User")
        notif = NotificationService.create_notification(
            user=user,
            title="Pickup Scheduled",
            message="Your pickup is confirmed for tomorrow morning.",
            notification_type=Notification.Types.PICKUP
        )
        assert notif.pk is not None
        assert notif.is_read is False

    def test_send_email_notification(self):
        NotificationService.send_email_notification(
            to_email="citizen@trashport.local",
            subject="Pickup Confirmed #123",
            template_base="pickup_confirmed",
            context={
                "user_name": "Citizen Alex",
                "pickup_id": 123,
                "scheduled_time": "Aug 23, 10:00 AM",
                "address": "123 Green St"
            }
        )
        assert len(mail.outbox) == 1
        assert "Pickup Confirmed #123" in mail.outbox[0].subject
