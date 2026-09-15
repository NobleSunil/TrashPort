"""
Database Seeding Script: Geographic Service Zones.

Initializes default urban coverage zones for TrashPort collection vehicles,
defining central coordinates, operation codes, and service radii in kilometers.

Usage:
    python scripts/seed_zones.py
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django
django.setup()

from trashport.core.maps.models import ServiceZone

def seed_zones():
    """Seeds predefined geographic circular service zones into the database."""
    print("Seeding geographic zones for TrashPort...")
    zones = [

        ("Central Eco Zone", "BLR-C01", 12.9716, 77.5946, 6.5),
        ("South Green Belt", "BLR-S02", 12.9250, 77.5890, 8.0),
        ("Tech Corridor East", "BLR-E03", 12.9850, 77.7200, 10.0),
        ("North Logistics Hub", "BLR-N04", 13.0350, 77.5970, 7.5),
    ]

    for name, code, lat, lon, radius in zones:
        zone, created = ServiceZone.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "center_latitude": lat,
                "center_longitude": lon,
                "radius_km": radius,
                "is_active": True,
            }
        )
        if created:
            print(f"Created zone: {name} ({code})")

    print("Zones seeded successfully!")

if __name__ == "__main__":
    seed_zones()
