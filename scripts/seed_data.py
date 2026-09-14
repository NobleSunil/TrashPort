import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django
django.setup()

from django.contrib.auth import get_user_model
from waste_management.models import WasteCategory, Address, PickupRequest
from django.utils import timezone

User = get_user_model()

def seed_demo_data():
    print("Seeding demo data for TrashPort...")

    # 1. Categories
    categories = [
        ("Dry Recyclables", "Paper, cardboard, clean plastics, glass bottles", 1.50, 10),
        ("Organic / Wet Waste", "Kitchen food waste, garden scraps, compostables", 0.50, 5),
        ("E-Waste", "Old electronics, cables, batteries, chargers", 5.00, 50),
        ("Hazardous & Medical", "Chemicals, paints, fluorescent bulbs, medicines", 10.00, 0),
    ]
    for name, desc, fee, pts in categories:
        cat, created = WasteCategory.objects.get_or_create(
            name=name,
            defaults={"description": desc, "fee_per_kg": fee, "points_per_kg": pts}
        )
        if created:
            print(f"Created category: {name}")

    # 3. Demo Users
    if not User.objects.filter(email="collector@trashport.local").exists():
        c = User.objects.create_user(
            email="collector@trashport.local",
            password="CollectorPass123!",
            name="Rajesh Kumar (Collector)",
            role=User.Roles.COLLECTOR,
        )
        print("Created demo collector: collector@trashport.local")

    if not User.objects.filter(email="citizen@trashport.local").exists():
        cit = User.objects.create_user(
            email="citizen@trashport.local",
            password="CitizenPass123!",
            name="Ananya Sharma",
            role=User.Roles.CITIZEN,
        )
        cit.wallet_points = 150
        cit.save()
        
        addr = Address.objects.create(
            user=cit,
            address_line1="42 Palm Avenue, Koramangala",
            address_line2="Near Green Park",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560034",
            is_default=True,
        )
        print("Created demo citizen: citizen@trashport.local")

    print("Demo data seeded successfully!")

if __name__ == "__main__":
    seed_demo_data()
