"""
Management command to seed initial operational Cities, Hubs, and Vehicles.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from trashport.core.waste_management.models import City, Hub, Vehicle

User = get_user_model()


class Command(BaseCommand):
    help = "Seed initial operational Cities, Hubs, and Vehicles"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Cities and Hubs..."))

        cities_data = [
            {
                "name": "Kochi",
                "state": "Kerala",
                "hub_name": "Kochi Central Hub",
                "lat": Decimal("9.931200"),
                "lng": Decimal("76.267300"),
                "address": "Marine Drive, Kochi, Kerala 682031",
                "vehicles": ["KL-07-TP-1001", "KL-07-TP-1002"],
                "has_collector": True,
            },
            {
                "name": "Thiruvananthapuram",
                "state": "Kerala",
                "hub_name": "Trivandrum South Hub",
                "lat": Decimal("8.524100"),
                "lng": Decimal("76.936600"),
                "address": "Pattom, Thiruvananthapuram, Kerala 695004",
                "vehicles": ["KL-01-TP-2001"],
                "has_collector": True,
            },
            {
                "name": "Kozhikode",
                "state": "Kerala",
                "hub_name": "Kozhikode City Hub",
                "lat": Decimal("11.258800"),
                "lng": Decimal("75.780400"),
                "address": "Mananchira, Kozhikode, Kerala 673001",
                "vehicles": ["KL-11-TP-3001"],
                "has_collector": False,  # Will test "service not available yet in this city"
            },
            {
                "name": "Thrissur",
                "state": "Kerala",
                "hub_name": "Thrissur Cultural Hub",
                "lat": Decimal("10.527600"),
                "lng": Decimal("76.214400"),
                "address": "Swaraj Round, Thrissur, Kerala 680001",
                "vehicles": ["KL-08-TP-4001"],
                "has_collector": False,
            },
            {
                "name": "Kollam",
                "state": "Kerala",
                "hub_name": "Kollam Coastal Hub",
                "lat": Decimal("8.893200"),
                "lng": Decimal("76.614100"),
                "address": "Chinnakada, Kollam, Kerala 691001",
                "vehicles": ["KL-02-TP-5001"],
                "has_collector": False,
            },
            {
                "name": "Bengaluru",
                "state": "Karnataka",
                "hub_name": "Bengaluru Central Hub",
                "lat": Decimal("12.971600"),
                "lng": Decimal("77.594600"),
                "address": "MG Road, Bengaluru, Karnataka 560001",
                "vehicles": ["KA-01-TP-6001"],
                "has_collector": True,
            },
        ]

        for item in cities_data:
            city, _ = City.objects.get_or_create(
                name=item["name"],
                defaults={"state": item["state"], "is_active": True}
            )

            hub, created = Hub.objects.get_or_create(
                name=item["hub_name"],
                defaults={
                    "city": city,
                    "latitude": item["lat"],
                    "longitude": item["lng"],
                    "address": item["address"],
                    "is_active": True,
                }
            )
            if not created:
                hub.city = city
                hub.latitude = item["lat"]
                hub.longitude = item["lng"]
                hub.address = item["address"]
                hub.is_active = True
                hub.save()

            # Seed vehicles
            for v_num in item.get("vehicles", []):
                Vehicle.objects.get_or_create(
                    vehicle_number=v_num,
                    defaults={
                        "hub": hub,
                        "max_capacity": 5,
                        "status": Vehicle.StatusChoices.AVAILABLE,
                    }
                )

            # Seed collector if specified
            if item.get("has_collector"):
                collector_email = f"collector.{item['name'].lower()}@trashport.in"
                collector, c_created = User.objects.get_or_create(
                    email=collector_email,
                    defaults={
                        "name": f"Collector {item['name']}",
                        "role": User.Roles.COLLECTOR,
                        "verification_status": User.VerificationStatus.APPROVED,
                        "is_active": True,
                    }
                )
                if c_created:
                    collector.set_password("TrashPort@123")
                    collector.save()
                collector.hub = hub

            self.stdout.write(self.style.SUCCESS(f"Processed city: {city.name} with hub: {hub.name}"))

        self.stdout.write(self.style.SUCCESS("Successfully seeded cities, hubs, and vehicles!"))
