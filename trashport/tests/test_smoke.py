"""Smoke test suite to verify core Django application health."""
from django.test import TestCase
from django.urls import reverse
from trashport.core.waste_management.models import WasteCategory

class CoreSmokeTest(TestCase):
    def test_environment_boots(self):
        """Verify Django settings and test runner initialize cleanly."""
        self.assertTrue(True)

    def test_waste_category_model(self):
        """Verify models can be created in the test database."""
        cat = WasteCategory.objects.create(
            name="Test Recyclables",
            description="Test waste category",
            fee_per_kg=2.50,
            points_per_kg=10,
        )
        self.assertEqual(cat.name, "Test Recyclables")
        self.assertEqual(float(cat.fee_per_kg), 2.50)

    def test_home_page_resolves(self):
        """Verify home page URL endpoint resolves."""
        response = self.client.get(reverse("home"))
        # Should either succeed or redirect to login
        self.assertIn(response.status_code, [200, 302])
