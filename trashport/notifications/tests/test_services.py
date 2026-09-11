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

    def test_pickup_and_payment_notification_lifecycle(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, WasteCategory, PickupRequest
        from trashport.payments.services import PaymentGatewayService

        # Clear mailbox
        mail.outbox = []

        citizen = User.objects.create_user(
            email="citizen_notify@trashport.local",
            name="Alice Citizen",
            role=User.Roles.CITIZEN,
        )
        collector = User.objects.create_user(
            email="collector_notify@trashport.local",
            name="Bob Collector",
            role=User.Roles.COLLECTOR,
            verification_status=User.VerificationStatus.APPROVED,
        )
        address = Address.objects.create(
            user=citizen,
            address_line1="456 Green Way",
            city="Kochi",
            state="Kerala",
            postal_code="682001",
        )
        category = WasteCategory.objects.create(
            name="Plastics",
            fee_per_kg=Decimal("5.00"),
            points_per_kg=2,
        )

        # 1. Event: Pickup requested / booked
        pickup = PickupRequest.objects.create(
            citizen=citizen,
            address=address,
            category=category,
            weight_kg=Decimal("10.00"),
            schedule_date=timezone.now(),
        )

        # Verify in-app and email for pickup requested
        req_notif = Notification.objects.filter(user=citizen, notification_type=Notification.Types.PICKUP).first()
        assert req_notif is not None
        assert "Confirmed" in req_notif.title
        assert len(mail.outbox) >= 1
        assert any("Pickup Request Confirmed" in m.subject for m in mail.outbox)

        # 2. Event: Collector assigned
        pickup.collector = collector
        pickup.status = PickupRequest.StatusChoices.ASSIGNED
        pickup.save()

        assigned_notif = Notification.objects.filter(
            user=citizen,
            notification_type=Notification.Types.PICKUP,
            title__contains="Collector Assigned"
        ).first()
        assert assigned_notif is not None
        assert "Bob Collector" in assigned_notif.message
        assert any("Collector Assigned" in m.subject for m in mail.outbox)

        # 3. Event: Payment completed & invoice sent
        pay_result = PaymentGatewayService.process_card_payment(
            user=citizen,
            pickup=pickup,
            card_number="4242424242424242",
            card_name="Alice Citizen",
            expiry="12/28",
            cvv="123",
        )
        assert pay_result["success"] is True
        pay_notif = Notification.objects.filter(
            user=citizen,
            notification_type=Notification.Types.PAYMENT
        ).first()
        assert pay_notif is not None
        assert "Payment Receipt" in pay_notif.title
        assert any("Payment Receipt" in m.subject for m in mail.outbox)

        # 4. Event: Pickup cancelled
        pickup.status = PickupRequest.StatusChoices.CANCELLED
        pickup.save()

        cancel_notif = Notification.objects.filter(
            user=citizen,
            notification_type=Notification.Types.PICKUP,
            title__contains="Cancelled"
        ).first()
        assert cancel_notif is not None
        assert any("Pickup Request Cancelled" in m.subject for m in mail.outbox)

    def test_clear_all_and_mark_all_read_notifications(self):
        from django.test import Client
        from django.urls import reverse

        user = User.objects.create_user(email="clear_user@trashport.local", name="Clear User")
        Notification.objects.create(user=user, title="Notice 1", message="Msg 1", is_read=False)
        Notification.objects.create(user=user, title="Notice 2", message="Msg 2", is_read=False)

        client = Client()
        client.force_login(user)

        # Mark all read
        res_read = client.post(reverse("notifications:mark_all_read"))
        assert res_read.status_code == 200
        assert Notification.objects.filter(user=user, is_read=False).count() == 0
        assert Notification.objects.filter(user=user).count() == 2

        # Clear all
        res_clear = client.post(reverse("notifications:clear_all"))
        assert res_clear.status_code == 200
        assert Notification.objects.filter(user=user).count() == 0


