from django.core import mail
from trashport.services.notifications.tasks import async_send_email_notification


def test_async_send_email_task():
    async_send_email_notification(
        to_email="async@trashport.local",
        subject="Async Alert",
        template_base="pickup_confirmed",
        context={"user_name": "Async User", "pickup_id": 999, "scheduled_time": "Now", "address": "Central Ave"}
    )
    assert len(mail.outbox) >= 1
