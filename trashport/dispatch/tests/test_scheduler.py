import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from waste_management.models import Address, WasteCategory, PickupRequest
from trashport.dispatch.scheduler import DispatchScheduler
from trashport.dispatch.models import DispatchBatch

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestDispatchScheduler:
    def test_run_auto_dispatch(self):
        admin = User.objects.create_superuser(
            email="admin_disp@trashport.local",
            password="password",
            role=User.Roles.ADMIN
        )
        citizen = User.objects.create_user(
            email="citizen_disp@trashport.local",
            name="Citizen",
            role=User.Roles.CITIZEN
        )
        collector = User.objects.create_user(
            email="coll_disp@trashport.local",
            name="Collector",
            role=User.Roles.COLLECTOR
        )

        cat = WasteCategory.objects.create(name="Free Recyclables", fee_per_kg=0.0)
        addr = Address.objects.create(
            user=citizen,
            address_line1="456 Elm St",
            city="City",
            state="Karnataka",
            postal_code="12345"
        )
        p = PickupRequest.objects.create(
            citizen=citizen,
            address=addr,
            category=cat,
            schedule_date=timezone.now(),
            status="PENDING"
        )

        batch = DispatchScheduler.run_auto_dispatch(algorithm="NEAREST", user=admin)
        assert isinstance(batch, DispatchBatch)
        assert batch.assigned_count == 1
        p.refresh_from_db()
        assert p.collector == collector
        assert p.status == "ASSIGNED"
