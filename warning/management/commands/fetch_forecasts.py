"""
Management command to fetch weather forecasts and generate heatwave alerts.

Fetches 7-day hourly forecast data from Open-Meteo for all (or one)
monitored locations, computes thermal indices, detects heatwaves,
creates alerts, and notifies subscribers.

Usage:
    python manage.py fetch_forecasts
    python manage.py fetch_forecasts --location Delhi
"""

from django.core.management.base import BaseCommand
from warning.services.forecast import fetch_all_forecasts
from warning.services.alerts import process_all_alerts


class Command(BaseCommand):
    help = 'Fetch weather forecasts from Open-Meteo and generate heatwave alerts'

    def add_arguments(self, parser):
        """Add optional --location argument for single-city fetch."""
        parser.add_argument(
            '--location',
            type=str,
            help='Fetch data for a specific location (partial name match)',
        )

    def handle(self, *args, **options):
        location_name = options.get('location')

        # ── Step 1: Fetch forecast data ──
        if location_name:
            self.stdout.write(f'Fetching forecasts for: {location_name}...')
        else:
            self.stdout.write('Fetching forecasts for all locations...')

        fetch_summary = fetch_all_forecasts(location_name)

        self.stdout.write(self.style.SUCCESS(
            f'\nFetch Summary:\n'
            f'  Locations processed: {fetch_summary["locations_processed"]}\n'
            f'  Total records stored: {fetch_summary["total_records"]}'
        ))

        if fetch_summary['errors']:
            self.stdout.write(self.style.WARNING('  Errors:'))
            for err in fetch_summary['errors']:
                self.stdout.write(f'    - {err}')

        # ── Step 2: Detect heatwaves and create alerts ──
        self.stdout.write('\nDetecting heatwaves and creating alerts...')
        alert_summary = process_all_alerts(location_name)

        self.stdout.write(self.style.SUCCESS(
            f'\nAlert Summary:\n'
            f'  Locations checked: {alert_summary["locations_processed"]}\n'
            f'  New alerts created: {alert_summary["alerts_created"]}'
        ))

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Forecast fetch and alert generation complete!'
        ))
