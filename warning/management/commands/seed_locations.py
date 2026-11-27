"""
Management command to seed the database with Indian cities,
cooling centers, and a demo user for HeatWatch.

Usage:
    python manage.py seed_locations
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from warning.models import Location, ShelterLocation, UserProfile


# 12 major Indian cities with their coordinates
CITIES = [
    {
        'name': 'Delhi',
        'latitude': 28.6139,
        'longitude': 77.2090,
        'state_region': 'Delhi',
        'population_note': 'Capital, 20M+ metro',
    },
    {
        'name': 'Jaipur',
        'latitude': 26.9124,
        'longitude': 75.7873,
        'state_region': 'Rajasthan',
        'population_note': 'Pink City, 3M+',
    },
    {
        'name': 'Nagpur',
        'latitude': 21.1458,
        'longitude': 79.0882,
        'state_region': 'Maharashtra',
        'population_note': 'Orange City, 2.5M+',
    },
    {
        'name': 'Ahmedabad',
        'latitude': 23.0225,
        'longitude': 72.5714,
        'state_region': 'Gujarat',
        'population_note': 'Textile hub, 5.5M+',
    },
    {
        'name': 'Hyderabad',
        'latitude': 17.3850,
        'longitude': 78.4867,
        'state_region': 'Telangana',
        'population_note': 'IT hub, 7M+',
    },
    {
        'name': 'Chennai',
        'latitude': 13.0827,
        'longitude': 80.2707,
        'state_region': 'Tamil Nadu',
        'population_note': 'Coastal city, 7M+',
    },
    {
        'name': 'Kolkata',
        'latitude': 22.5726,
        'longitude': 88.3639,
        'state_region': 'West Bengal',
        'population_note': 'Cultural capital, 14M+',
    },
    {
        'name': 'Mumbai',
        'latitude': 19.0760,
        'longitude': 72.8777,
        'state_region': 'Maharashtra',
        'population_note': 'Financial capital, 20M+',
    },
    {
        'name': 'Lucknow',
        'latitude': 26.8467,
        'longitude': 80.9462,
        'state_region': 'Uttar Pradesh',
        'population_note': 'City of Nawabs, 3M+',
    },
    {
        'name': 'Bhopal',
        'latitude': 23.2599,
        'longitude': 77.4126,
        'state_region': 'Madhya Pradesh',
        'population_note': 'City of Lakes, 2M+',
    },
    {
        'name': 'Varanasi',
        'latitude': 25.3176,
        'longitude': 83.0068,
        'state_region': 'Uttar Pradesh',
        'population_note': 'Holy city, 1.5M+',
    },
    {
        'name': 'Pune',
        'latitude': 18.5204,
        'longitude': 73.8567,
        'state_region': 'Maharashtra',
        'population_note': 'Education hub, 3M+',
    },
    # 3 real hot global cities (Southern Hemisphere / Equatorial summer heat)
    {
        'name': 'Alice Springs',
        'latitude': -23.6980,
        'longitude': 133.8807,
        'state_region': 'Australia (NT)',
        'population_note': 'Outback desert hub, extreme summer heat',
    },
    {
        'name': 'Darwin',
        'latitude': -12.4634,
        'longitude': 130.8456,
        'state_region': 'Australia (NT)',
        'population_note': 'Tropical northern coast, high humidity',
    },
    {
        'name': 'Jakarta',
        'latitude': -6.2088,
        'longitude': 106.8456,
        'state_region': 'Indonesia',
        'population_note': 'Equatorial megacity, 10M+',
    },
]

# Sample cooling centers near major cities
SHELTERS = [
    {
        'name': 'Delhi Community Cooling Center',
        'lat': 28.6200, 'lon': 77.2100,
        'address': 'Near Connaught Place, New Delhi',
        'city': 'Delhi',
    },
    {
        'name': 'Jaipur Public Library Shelter',
        'lat': 26.9150, 'lon': 75.7900,
        'address': 'MI Road, Jaipur',
        'city': 'Jaipur',
    },
    {
        'name': 'Nagpur Central Mall AC Zone',
        'lat': 21.1500, 'lon': 79.0900,
        'address': 'Sitabuldi, Nagpur',
        'city': 'Nagpur',
    },
    {
        'name': 'Ahmedabad Relief Camp',
        'lat': 23.0300, 'lon': 72.5800,
        'address': 'Ashram Road, Ahmedabad',
        'city': 'Ahmedabad',
    },
    {
        'name': 'Hyderabad Metro Station Shelter',
        'lat': 17.3900, 'lon': 78.4900,
        'address': 'Ameerpet Metro, Hyderabad',
        'city': 'Hyderabad',
    },
    {
        'name': 'Chennai Beach Public Shelter',
        'lat': 13.0600, 'lon': 80.2800,
        'address': 'Marina Beach Road, Chennai',
        'city': 'Chennai',
    },
    {
        'name': 'Kolkata Park Street AC Hall',
        'lat': 22.5500, 'lon': 88.3500,
        'address': 'Park Street, Kolkata',
        'city': 'Kolkata',
    },
    {
        'name': 'Mumbai BMC Cooling Center',
        'lat': 19.0800, 'lon': 72.8800,
        'address': 'Dadar, Mumbai',
        'city': 'Mumbai',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with Indian cities, cooling centers, and a demo user'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding locations...'))

        # ── Seed cities ──
        created_count = 0
        for city_data in CITIES:
            loc, created = Location.objects.get_or_create(
                name=city_data['name'],
                defaults={
                    'latitude': city_data['latitude'],
                    'longitude': city_data['longitude'],
                    'state_region': city_data['state_region'],
                    'population_note': city_data['population_note'],
                }
            )
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f"  {status}: {loc.name} ({loc.state_region})")
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nLocations: {created_count} created, '
            f'{len(CITIES) - created_count} already existed'
        ))

        # ── Seed cooling centers ──
        shelter_count = 0
        for shelter_data in SHELTERS:
            city = Location.objects.filter(name=shelter_data['city']).first()
            if city:
                _, created = ShelterLocation.objects.get_or_create(
                    name=shelter_data['name'],
                    defaults={
                        'latitude': shelter_data['lat'],
                        'longitude': shelter_data['lon'],
                        'address': shelter_data['address'],
                        'location': city,
                    }
                )
                if created:
                    shelter_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Cooling centers: {shelter_count} created'
        ))

        # ── Create demo user ──
        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@heatwatch.example.com',
                'is_active': True,
            }
        )
        if created:
            demo_user.set_password('demo1234')
            demo_user.save()
            UserProfile.objects.get_or_create(
                user=demo_user,
                defaults={'group_type': 'GENERAL'}
            )
            self.stdout.write(self.style.SUCCESS(
                'Demo user created: username=demo, password=demo1234'
            ))
        else:
            self.stdout.write('Demo user already exists')

        # ── Superuser note ──
        self.stdout.write(self.style.WARNING(
            '\nNote: To create a superuser, run:\n'
            '  python manage.py createsuperuser'
        ))
        self.stdout.write(self.style.SUCCESS('\n✓ Seeding complete!'))
