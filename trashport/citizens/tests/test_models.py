import pytest
from django.contrib.auth import get_user_model
from waste_management.models import Address

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_citizen_address_creation():
    user = User.objects.create_user(email="citmodel@trashport.local", name="Cit Model")
    addr = Address.objects.create(
        user=user,
        address_line1="100 Green St",
        city="EcoCity",
        state="Karnataka",
        postal_code="560001",
    )
    assert addr.pk is not None
    assert str(addr) == f"100 Green St, EcoCity ({user.email})"
