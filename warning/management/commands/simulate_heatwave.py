"""
Management command to simulate heatwave conditions for testing and viva presentation.

Injects realistic peak summer temperatures (42°C - 46°C) for selected cities
(e.g., Delhi, Jaipur, Nagpur, Ahmedabad) over a 5-day period, computes Heat Index
and Wet-Bulb temperatures, runs the heatwave detection algorithm, generates
active Alert records in the database, and dispatches email notifications to subscribers.

Usage:
    python manage.py simulate_heatwave          # Injects heatwave scenario (for viva demo)
    python manage.py simulate_heatwave --reset  # Restores real live forecasts from Open-Meteo
"""

from datetime import datetime, timedelta, timezone as dt_timezone
import random
from django.core.management.base import BaseCommand
from django.utils import timezone

from warning.models import Location, ForecastRecord, Alert, Subscription, User
from warning.services.indices import compute_heat_index, compute_wet_bulb, classify_risk
from warning.services.alerts import process_all_alerts
from warning.services.forecast import fetch_all_forecasts


class Command(BaseCommand):
    help = 'Simulate peak summer heatwave scenario for viva/demo presentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset back to real live forecast data from Open-Meteo'
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.NOTICE('Resetting to real live Open-Meteo data...'))
            ForecastRecord.objects.all().delete()
            Alert.objects.all().delete()
            summary = fetch_all_forecasts()
            process_all_alerts()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Successfully restored real live weather data! '
                f'({summary["total_records"]} records for {summary["locations_processed"]} cities)'
            ))
            return

        self.stdout.write(self.style.NOTICE(
            '=== Injecting Peak Summer Heatwave Simulation Scenario ===\n'
            'This simulates a realistic May/June heatwave so you can demonstrate\n'
            'disaster alerts and thermal stress in your college evaluation/viva.\n'
        ))

        hot_city_names = ['Delhi', 'Jaipur', 'Nagpur', 'Ahmedabad']
        hot_cities = Location.objects.filter(name__in=hot_city_names)

        if not hot_cities.exists():
            self.stdout.write(self.style.ERROR(
                'No matching cities found. Run python manage.py seed_locations first.'
            ))
            return

        # Ensure demo user has a subscription to see console notifications
        demo_user = User.objects.filter(username='demo').first()
        if demo_user:
            for city in hot_cities:
                Subscription.objects.get_or_create(
                    user=demo_user,
                    location=city,
                    defaults={'min_level': 'CAUTION'}
                )

        now = timezone.now()
        start_time = now.replace(minute=0, second=0, microsecond=0)

        # Clear existing records for these cities
        ForecastRecord.objects.filter(location__in=hot_cities).delete()
        Alert.objects.filter(location__in=hot_cities).delete()

        records_created = 0
        # Generate 7 days of realistic summer hourly data (168 hours)
        for loc in hot_cities:
            for h in range(168):
                timestamp = start_time + timedelta(hours=h)
                hour_of_day = timestamp.hour

                # Realistic diurnal cycle: cooler at night (31-33°C), peaking 13:00-16:00 (43-46°C)
                if 12 <= hour_of_day <= 16:
                    temp = round(random.uniform(43.5, 46.2), 1)
                    humidity = round(random.uniform(38.0, 52.0), 1)
                elif 8 <= hour_of_day <= 19:
                    temp = round(random.uniform(37.0, 42.0), 1)
                    humidity = round(random.uniform(40.0, 60.0), 1)
                else:
                    temp = round(random.uniform(30.5, 34.0), 1)
                    humidity = round(random.uniform(55.0, 70.0), 1)

                hi = compute_heat_index(temp, humidity)
                wb = compute_wet_bulb(temp, humidity)
                risk = classify_risk(hi)

                ForecastRecord.objects.create(
                    location=loc,
                    timestamp=timestamp,
                    temperature_c=temp,
                    humidity=humidity,
                    heat_index_c=hi,
                    wet_bulb_c=wb,
                    risk_level=risk,
                )
                records_created += 1

        self.stdout.write(f'Created {records_created} simulated summer forecast records.')
        self.stdout.write('Running automated heatwave detection and alert dispatch...')

        summary = process_all_alerts()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Heatwave Simulation Complete!\n'
            f'  - Hot Cities Simulated: {", ".join(hot_city_names)}\n'
            f'  - Active Alerts Created: {summary["alerts_created"]}\n'
            f'  - Peak Heat Indices: 48°C - 56°C (Danger / Extreme Danger)\n'
            f'  - Subscriber Notifications: Dispatched to console!\n\n'
            f'Visit http://127.0.0.1:8000/ to view the active disaster dashboard.\n'
            f'To restore real live winter weather anytime, run:\n'
            f'  python manage.py simulate_heatwave --reset\n'
        ))
