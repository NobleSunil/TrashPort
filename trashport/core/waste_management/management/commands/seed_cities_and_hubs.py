"""
Management command to seed initial operational Cities, Hubs, and Vehicles.
"""
import re
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
            # -----------------------------------------------------------------
            # 1. Thiruvananthapuram District
            # -----------------------------------------------------------------
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
                "name": "Venganoor Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Venganoor Hub",
                "lat": Decimal("8.423900"),
                "lng": Decimal("76.994000"),
                "address": "Panchayath Junction, Venganoor, Thiruvananthapuram 695523",
                "vehicles": ["KL-01-TP-2002"],
                "has_collector": True,
            },
            {
                "name": "Kazhakkoottam",
                "state": "Kerala",
                "hub_name": "Technopark Kazhakkoottam Hub",
                "lat": Decimal("8.568600"),
                "lng": Decimal("76.873100"),
                "address": "Technopark Phase 1, Kazhakkoottam, Thiruvananthapuram 695581",
                "vehicles": ["KL-01-TP-2003"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 2. Kollam District
            # -----------------------------------------------------------------
            {
                "name": "Kollam",
                "state": "Kerala",
                "hub_name": "Kollam Coastal Hub",
                "lat": Decimal("8.893200"),
                "lng": Decimal("76.614100"),
                "address": "Chinnakada, Kollam, Kerala 691001",
                "vehicles": ["KL-02-TP-5001"],
                "has_collector": True,
            },
            {
                "name": "Mayyanad Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Mayyanad Hub",
                "lat": Decimal("8.835800"),
                "lng": Decimal("76.645000"),
                "address": "Railway Station Road, Mayyanad, Kollam 691303",
                "vehicles": ["KL-02-TP-5002"],
                "has_collector": True,
            },
            {
                "name": "Sasthamkotta Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Sasthamkotta Lake Hub",
                "lat": Decimal("9.043500"),
                "lng": Decimal("76.627200"),
                "address": "Lake Junction, Sasthamkotta, Kollam 690521",
                "vehicles": ["KL-02-TP-5003"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # 3. Pathanamthitta District
            # -----------------------------------------------------------------
            {
                "name": "Kozhencherry Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kozhencherry Hub",
                "lat": Decimal("9.340000"),
                "lng": Decimal("76.710000"),
                "address": "Bridge Road, Kozhencherry, Pathanamthitta 689641",
                "vehicles": ["KL-03-TP-3001"],
                "has_collector": True,
            },
            {
                "name": "Aranmula Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Aranmula Heritage Hub",
                "lat": Decimal("9.314200"),
                "lng": Decimal("76.685300"),
                "address": "Temple Road, Aranmula, Pathanamthitta 689533",
                "vehicles": ["KL-03-TP-3002"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 4. Alappuzha District
            # -----------------------------------------------------------------
            {
                "name": "Mararikulam Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Mararikulam Beach Hub",
                "lat": Decimal("9.601500"),
                "lng": Decimal("76.311700"),
                "address": "Beach Road, Mararikulam North, Alappuzha 688523",
                "vehicles": ["KL-04-TP-4001"],
                "has_collector": True,
            },
            {
                "name": "Kainakary Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kainakary Backwaters Hub",
                "lat": Decimal("9.516000"),
                "lng": Decimal("76.388700"),
                "address": "Boat Jetty, Kainakary, Alappuzha 688501",
                "vehicles": ["KL-04-TP-4002"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 5. Kottayam District
            # -----------------------------------------------------------------
            {
                "name": "Kumarakom Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kumarakom Backwater Hub",
                "lat": Decimal("9.617500"),
                "lng": Decimal("76.430100"),
                "address": "Boat Jetty Road, Kumarakom, Kottayam 686563",
                "vehicles": ["KL-05-TP-5001"],
                "has_collector": True,
            },
            {
                "name": "Ettumanoor",
                "state": "Kerala",
                "hub_name": "Ettumanoor Temple Hub",
                "lat": Decimal("9.670600"),
                "lng": Decimal("76.561500"),
                "address": "MC Road, Ettumanoor, Kottayam 686631",
                "vehicles": ["KL-05-TP-5002"],
                "has_collector": True,
            },
            {
                "name": "Meenachil Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Pala Meenachil Hub",
                "lat": Decimal("9.712600"),
                "lng": Decimal("76.683300"),
                "address": "Bypass Road, Meenachil, Pala, Kottayam 686575",
                "vehicles": ["KL-05-TP-5003"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 6. Idukki District
            # -----------------------------------------------------------------
            {
                "name": "Munnar Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Munnar Hills Hub",
                "lat": Decimal("10.088900"),
                "lng": Decimal("77.059500"),
                "address": "Old Munnar Market Road, Munnar, Idukki 685612",
                "vehicles": ["KL-06-TP-6001"],
                "has_collector": True,
            },
            {
                "name": "Adimali Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Adimali Valley Hub",
                "lat": Decimal("10.015000"),
                "lng": Decimal("76.954000"),
                "address": "National Highway 85, Adimali, Idukki 685561",
                "vehicles": ["KL-06-TP-6002"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # 7. Ernakulam District
            # -----------------------------------------------------------------
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
                "name": "Mulavukad Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Mulavukad Island Hub",
                "lat": Decimal("9.995000"),
                "lng": Decimal("76.265000"),
                "address": "Bolgatty Road, Mulavukad, Ernakulam 682504",
                "vehicles": ["KL-07-TP-1003"],
                "has_collector": True,
            },
            {
                "name": "Kumbalangi Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kumbalangi Eco Hub",
                "lat": Decimal("9.874400"),
                "lng": Decimal("76.284700"),
                "address": "Model Tourism Village, Kumbalangi, Ernakulam 682007",
                "vehicles": ["KL-07-TP-1004"],
                "has_collector": True,
            },
            {
                "name": "Aluva",
                "state": "Kerala",
                "hub_name": "Aluva Periyar Hub",
                "lat": Decimal("10.107600"),
                "lng": Decimal("76.351600"),
                "address": "Periyar River Bank, Aluva, Ernakulam 683101",
                "vehicles": ["KL-07-TP-1005"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 8. Thrissur District
            # -----------------------------------------------------------------
            {
                "name": "Thrissur",
                "state": "Kerala",
                "hub_name": "Thrissur Cultural Hub",
                "lat": Decimal("10.527600"),
                "lng": Decimal("76.214400"),
                "address": "Swaraj Round, Thrissur, Kerala 680001",
                "vehicles": ["KL-08-TP-4001"],
                "has_collector": True,
            },
            {
                "name": "Cherpu Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Cherpu Heritage Hub",
                "lat": Decimal("10.457800"),
                "lng": Decimal("76.208100"),
                "address": "Main Road, Cherpu, Thrissur 680561",
                "vehicles": ["KL-08-TP-4002"],
                "has_collector": True,
            },
            {
                "name": "Guruvayur",
                "state": "Kerala",
                "hub_name": "Guruvayur Municipal Hub",
                "lat": Decimal("10.594600"),
                "lng": Decimal("76.040000"),
                "address": "East Nada, Guruvayur, Thrissur 680101",
                "vehicles": ["KL-08-TP-4003"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 9. Palakkad District
            # -----------------------------------------------------------------
            {
                "name": "Malampuzha Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Malampuzha Dam Hub",
                "lat": Decimal("10.835000"),
                "lng": Decimal("76.685000"),
                "address": "Garden Road, Malampuzha, Palakkad 678651",
                "vehicles": ["KL-09-TP-9001"],
                "has_collector": True,
            },
            {
                "name": "Chittur-Thathamangalam",
                "state": "Kerala",
                "hub_name": "Chittur Agri Hub",
                "lat": Decimal("10.702500"),
                "lng": Decimal("76.719600"),
                "address": "Kacheri Medu, Chittur, Palakkad 678101",
                "vehicles": ["KL-09-TP-9002"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # 10. Malappuram District
            # -----------------------------------------------------------------
            {
                "name": "Kondotty Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kondotty Airport Hub",
                "lat": Decimal("11.144400"),
                "lng": Decimal("75.964400"),
                "address": "Airport Road, Kondotty, Malappuram 673638",
                "vehicles": ["KL-10-TP-1001"],
                "has_collector": True,
            },
            {
                "name": "Kottakkal",
                "state": "Kerala",
                "hub_name": "Kottakkal Ayurveda Hub",
                "lat": Decimal("11.002200"),
                "lng": Decimal("75.998300"),
                "address": "Arya Vaidya Sala Rd, Kottakkal, Malappuram 676503",
                "vehicles": ["KL-10-TP-1002"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 11. Kozhikode District
            # -----------------------------------------------------------------
            {
                "name": "Kozhikode",
                "state": "Kerala",
                "hub_name": "Kozhikode City Hub",
                "lat": Decimal("11.258800"),
                "lng": Decimal("75.780400"),
                "address": "Mananchira, Kozhikode, Kerala 673001",
                "vehicles": ["KL-11-TP-3001"],
                "has_collector": True,
            },
            {
                "name": "Kunnamangalam Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Kunnamangalam Knowledge Hub",
                "lat": Decimal("11.306900"),
                "lng": Decimal("75.875300"),
                "address": "NIT Campus Road, Kunnamangalam, Kozhikode 673571",
                "vehicles": ["KL-11-TP-3002"],
                "has_collector": True,
            },
            {
                "name": "Beypore Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Beypore Port Hub",
                "lat": Decimal("11.181600"),
                "lng": Decimal("75.804900"),
                "address": "Port Road, Beypore, Kozhikode 673015",
                "vehicles": ["KL-11-TP-3003"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # 12. Wayanad District
            # -----------------------------------------------------------------
            {
                "name": "Meppadi Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Meppadi Chembra Hub",
                "lat": Decimal("11.552800"),
                "lng": Decimal("76.128300"),
                "address": "Ooty Road, Meppadi, Wayanad 673577",
                "vehicles": ["KL-12-TP-2001"],
                "has_collector": True,
            },
            {
                "name": "Vythiri Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Vythiri Rainforest Hub",
                "lat": Decimal("11.550000"),
                "lng": Decimal("76.039000"),
                "address": "Ghat Road, Vythiri, Wayanad 673576",
                "vehicles": ["KL-12-TP-2002"],
                "has_collector": True,
            },
            {
                "name": "Sulthan Bathery",
                "state": "Kerala",
                "hub_name": "Bathery Wildlife Hub",
                "lat": Decimal("11.662200"),
                "lng": Decimal("76.257000"),
                "address": "Mysore Road, Sulthan Bathery, Wayanad 673592",
                "vehicles": ["KL-12-TP-2003"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # 13. Kannur District
            # -----------------------------------------------------------------
            {
                "name": "Dharmadam Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Dharmadam Island Hub",
                "lat": Decimal("11.773800"),
                "lng": Decimal("75.468200"),
                "address": "Beach Road, Dharmadam, Kannur 670106",
                "vehicles": ["KL-13-TP-1001"],
                "has_collector": True,
            },
            {
                "name": "Payyannur",
                "state": "Kerala",
                "hub_name": "Payyannur Subrahmanya Hub",
                "lat": Decimal("12.100000"),
                "lng": Decimal("75.200000"),
                "address": "Subrahmanya Swami Temple Road, Payyannur, Kannur 670307",
                "vehicles": ["KL-13-TP-1002"],
                "has_collector": True,
            },

            # -----------------------------------------------------------------
            # 14. Kasaragod District
            # -----------------------------------------------------------------
            {
                "name": "Udma Grama Panchayat",
                "state": "Kerala",
                "hub_name": "Bekal Fort Udma Hub",
                "lat": Decimal("12.385000"),
                "lng": Decimal("75.034000"),
                "address": "Bekal Fort Junction, Udma, Kasaragod 671319",
                "vehicles": ["KL-14-TP-1001"],
                "has_collector": True,
            },
            {
                "name": "Nileshwaram",
                "state": "Kerala",
                "hub_name": "Nileshwaram Cultural Hub",
                "lat": Decimal("12.253300"),
                "lng": Decimal("75.127500"),
                "address": "Palace Road, Nileshwaram, Kasaragod 671314",
                "vehicles": ["KL-14-TP-1002"],
                "has_collector": False,
            },

            # -----------------------------------------------------------------
            # Inter-state reference
            # -----------------------------------------------------------------
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
                clean_slug = re.sub(r"[^a-zA-Z0-9]+", ".", item["name"].lower()).strip(".")
                collector_email = f"collector.{clean_slug}@trashport.in"
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
