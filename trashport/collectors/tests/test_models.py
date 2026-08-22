import pytest
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_collector_role_creation():
    user = User.objects.create_user(
        email="colmodel@trashport.local",
        name="Col Model",
        role=User.Roles.COLLECTOR
    )
    assert user.role == User.Roles.COLLECTOR
