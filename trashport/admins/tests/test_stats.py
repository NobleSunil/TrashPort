import pytest
from django.contrib.auth import get_user_model
from trashport.core.waste_management.models import WasteCategory

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_admin_master_models():
    cat = WasteCategory.objects.create(name="Battery & Chemical", fee_per_kg=5.0)
    assert cat.pk is not None

