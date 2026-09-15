import pytest
from trashport.services.firebase.signals import firebase_user_authenticated
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_firebase_signal_emits():
    user = User.objects.create_user(email="signaltest@trashport.local", name="Signal Test")
    # Trigger signal and ensure no exceptions
    firebase_user_authenticated.send(
        sender=None,
        user=user,
        decoded_token={"uid": "signal123", "email": user.email}
    )
    assert user.pk is not None
