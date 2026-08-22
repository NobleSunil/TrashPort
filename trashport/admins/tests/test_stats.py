import pytest
from django.contrib.auth import get_user_model
from waste_management.models import WasteCategory, SubscriptionTier

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_admin_master_models():
    cat = WasteCategory.objects.create(name="Battery & Chemical", fee_per_kg=5.0)
    tier = SubscriptionTier.objects.create(name="Commercial Heavy", price=199.00, is_active=True)
    assert cat.pk is not None
    assert tier.pk is not None
