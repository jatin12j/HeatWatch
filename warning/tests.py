"""
Tests for the HeatWatch warning application.

Tests cover:
  - Thermal index calculations (heat index, wet-bulb, risk classification)
  - Heatwave detection logic (with mocked data)
  - View responses (dashboard, calculator, location detail, etc.)
  - Forecast fetching (with mocked API responses)

Run with: python manage.py test warning
"""

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Location, ForecastRecord, Alert, Subscription, UserProfile
from .services.indices import (
    compute_heat_index, compute_wet_bulb, classify_risk,
    celsius_to_fahrenheit, fahrenheit_to_celsius,
)
from .services.alerts import detect_heatwave_runs, create_alerts_for_location


# ══════════════════════════════════════════════
# Temperature Conversion Tests
# ══════════════════════════════════════════════

class TemperatureConversionTest(TestCase):
    """Test temperature unit conversions."""

    def test_celsius_to_fahrenheit_freezing(self):
        """0°C should be 32°F."""
        self.assertAlmostEqual(celsius_to_fahrenheit(0), 32.0)

    def test_celsius_to_fahrenheit_boiling(self):
        """100°C should be 212°F."""
        self.assertAlmostEqual(celsius_to_fahrenheit(100), 212.0)

    def test_celsius_to_fahrenheit_body_temp(self):
        """37°C should be 98.6°F."""
        self.assertAlmostEqual(celsius_to_fahrenheit(37), 98.6)

    def test_fahrenheit_to_celsius_freezing(self):
        """32°F should be 0°C."""
        self.assertAlmostEqual(fahrenheit_to_celsius(32), 0.0)

    def test_fahrenheit_to_celsius_boiling(self):
        """212°F should be 100°C."""
        self.assertAlmostEqual(fahrenheit_to_celsius(212), 100.0)


# ══════════════════════════════════════════════
# Heat Index Tests
# ══════════════════════════════════════════════

class HeatIndexTest(TestCase):
    """Test the NWS Heat Index calculation."""

    def test_moderate_conditions(self):
        """25°C at 40% RH should give roughly Normal conditions."""
        hi = compute_heat_index(25, 40)
        self.assertLess(hi, 27)  # Should be Normal risk

    def test_hot_humid(self):
        """35°C at 70% RH should give roughly 50°C heat index."""
        hi = compute_heat_index(35, 70)
        self.assertGreater(hi, 45)
        self.assertLess(hi, 55)

    def test_hot_dry(self):
        """40°C at 20% RH should still produce elevated heat index."""
        hi = compute_heat_index(40, 20)
        self.assertGreater(hi, 35)

    def test_cool_conditions(self):
        """20°C at 50% RH should return close to actual temperature."""
        hi = compute_heat_index(20, 50)
        self.assertAlmostEqual(hi, 20, delta=5)

    def test_humidity_clamping(self):
        """Humidity above 100 should be clamped to 100."""
        hi1 = compute_heat_index(35, 110)  # Clamped to 100
        hi2 = compute_heat_index(35, 100)
        self.assertAlmostEqual(hi1, hi2, delta=0.5)

    def test_returns_float(self):
        """Heat index should return a float."""
        hi = compute_heat_index(30, 50)
        self.assertIsInstance(hi, float)


# ══════════════════════════════════════════════
# Wet-Bulb Temperature Tests
# ══════════════════════════════════════════════

class WetBulbTest(TestCase):
    """Test the Stull (2011) Wet-Bulb Temperature calculation."""

    def test_moderate(self):
        """Wet-bulb should be less than dry-bulb temperature."""
        wb = compute_wet_bulb(30, 50)
        self.assertLess(wb, 30)
        self.assertGreater(wb, 15)

    def test_high_humidity(self):
        """At 99% RH, wet-bulb should be close to dry-bulb."""
        wb = compute_wet_bulb(25, 99)
        self.assertAlmostEqual(wb, 25, delta=2)

    def test_returns_float(self):
        """Wet-bulb should return a float."""
        wb = compute_wet_bulb(30, 50)
        self.assertIsInstance(wb, float)


# ══════════════════════════════════════════════
# Risk Classification Tests
# ══════════════════════════════════════════════

class RiskClassificationTest(TestCase):
    """Test the risk level classification."""

    def test_normal(self):
        self.assertEqual(classify_risk(20), 'NORMAL')

    def test_caution(self):
        self.assertEqual(classify_risk(28), 'CAUTION')

    def test_extreme_caution(self):
        self.assertEqual(classify_risk(35), 'EXTREME_CAUTION')

    def test_danger(self):
        self.assertEqual(classify_risk(42), 'DANGER')

    def test_extreme_danger(self):
        self.assertEqual(classify_risk(52), 'EXTREME_DANGER')

    def test_vulnerable_lowers_thresholds(self):
        """Vulnerable groups should have thresholds 3°C lower.
        25°C is Normal for general but Caution for vulnerable (27-3=24)."""
        self.assertEqual(classify_risk(25, vulnerable=False), 'NORMAL')
        self.assertEqual(classify_risk(25, vulnerable=True), 'CAUTION')

    def test_boundary_caution(self):
        """Exactly 27°C should be Caution."""
        self.assertEqual(classify_risk(27), 'CAUTION')

    def test_boundary_below_caution(self):
        """26.9°C should be Normal."""
        self.assertEqual(classify_risk(26.9), 'NORMAL')

    def test_boundary_danger(self):
        """Exactly 39°C should be Danger."""
        self.assertEqual(classify_risk(39), 'DANGER')

    def test_boundary_extreme_danger(self):
        """Exactly 51°C should be Extreme Danger."""
        self.assertEqual(classify_risk(51), 'EXTREME_DANGER')


# ══════════════════════════════════════════════
# Heatwave Detection Tests
# ══════════════════════════════════════════════

class HeatwaveDetectionTest(TestCase):
    """Test heatwave run detection with mocked daily data."""

    def test_no_heatwave(self):
        """No days above threshold should return no runs."""
        daily = [
            {'date': date(2024, 5, 1), 'max_hi': 35.0, 'risk_level': 'EXTREME_CAUTION'},
            {'date': date(2024, 5, 2), 'max_hi': 36.0, 'risk_level': 'EXTREME_CAUTION'},
            {'date': date(2024, 5, 3), 'max_hi': 37.0, 'risk_level': 'EXTREME_CAUTION'},
        ]
        runs = detect_heatwave_runs(daily, threshold=39.0, min_days=3)
        self.assertEqual(len(runs), 0)

    def test_exactly_three_days(self):
        """Exactly 3 consecutive days above threshold = one heatwave."""
        daily = [
            {'date': date(2024, 5, 1), 'max_hi': 40.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 2), 'max_hi': 42.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 3), 'max_hi': 41.0, 'risk_level': 'DANGER'},
        ]
        runs = detect_heatwave_runs(daily, threshold=39.0, min_days=3)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['start_date'], date(2024, 5, 1))
        self.assertEqual(runs[0]['end_date'], date(2024, 5, 3))
        self.assertAlmostEqual(runs[0]['peak_hi'], 42.0)

    def test_two_separate_runs(self):
        """Two separate runs of 3+ days should both be detected."""
        daily = [
            {'date': date(2024, 5, 1), 'max_hi': 40.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 2), 'max_hi': 41.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 3), 'max_hi': 42.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 4), 'max_hi': 30.0, 'risk_level': 'CAUTION'},
            {'date': date(2024, 5, 5), 'max_hi': 43.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 6), 'max_hi': 44.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 7), 'max_hi': 45.0, 'risk_level': 'DANGER'},
        ]
        runs = detect_heatwave_runs(daily, threshold=39.0, min_days=3)
        self.assertEqual(len(runs), 2)

    def test_too_few_consecutive_days(self):
        """Only 2 consecutive days should NOT trigger a heatwave."""
        daily = [
            {'date': date(2024, 5, 1), 'max_hi': 40.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 2), 'max_hi': 41.0, 'risk_level': 'DANGER'},
            {'date': date(2024, 5, 3), 'max_hi': 30.0, 'risk_level': 'CAUTION'},
        ]
        runs = detect_heatwave_runs(daily, threshold=39.0, min_days=3)
        self.assertEqual(len(runs), 0)

    def test_long_run(self):
        """A single long run of 7 days should be detected as one heatwave."""
        daily = [
            {'date': date(2024, 5, i), 'max_hi': 40.0 + i, 'risk_level': 'DANGER'}
            for i in range(1, 8)
        ]
        runs = detect_heatwave_runs(daily, threshold=39.0, min_days=3)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['days'], 7)


# ══════════════════════════════════════════════
# Alert Creation Tests
# ══════════════════════════════════════════════

class AlertCreationTest(TestCase):
    """Test alert creation with actual forecast data in DB."""

    def setUp(self):
        self.location = Location.objects.create(
            name='Test City', latitude=28.6, longitude=77.2
        )

    def test_creates_alert_for_heatwave(self):
        """Should create an alert when heatwave conditions exist."""
        base_time = timezone.now()
        for day_offset in range(4):
            for hour in range(24):
                ForecastRecord.objects.create(
                    location=self.location,
                    timestamp=base_time + timedelta(days=day_offset, hours=hour),
                    temperature_c=42.0,
                    humidity=50.0,
                    heat_index_c=48.0,
                    wet_bulb_c=30.0,
                    risk_level='DANGER',
                )

        alerts = create_alerts_for_location(self.location)
        self.assertGreaterEqual(len(alerts), 1)

    def test_no_alert_for_normal_conditions(self):
        """Should not create an alert for normal conditions."""
        base_time = timezone.now()
        for day_offset in range(4):
            for hour in range(24):
                ForecastRecord.objects.create(
                    location=self.location,
                    timestamp=base_time + timedelta(days=day_offset, hours=hour),
                    temperature_c=25.0,
                    humidity=40.0,
                    heat_index_c=24.0,
                    wet_bulb_c=16.0,
                    risk_level='NORMAL',
                )

        alerts = create_alerts_for_location(self.location)
        self.assertEqual(len(alerts), 0)

    def test_no_duplicate_alerts(self):
        """Running alert creation twice should not create duplicate alerts."""
        base_time = timezone.now()
        for day_offset in range(4):
            for hour in range(24):
                ForecastRecord.objects.create(
                    location=self.location,
                    timestamp=base_time + timedelta(days=day_offset, hours=hour),
                    temperature_c=42.0,
                    humidity=50.0,
                    heat_index_c=48.0,
                    wet_bulb_c=30.0,
                    risk_level='DANGER',
                )

        alerts1 = create_alerts_for_location(self.location)
        alerts2 = create_alerts_for_location(self.location)
        # Second call should create no new alerts
        self.assertEqual(len(alerts2), 0)


# ══════════════════════════════════════════════
# View Tests
# ══════════════════════════════════════════════

class ViewTests(TestCase):
    """Test that all views return expected status codes."""

    def setUp(self):
        self.client = Client()
        self.location = Location.objects.create(
            name='Delhi', latitude=28.6139, longitude=77.2090
        )
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            email='test@example.com'
        )
        UserProfile.objects.create(user=self.user, group_type='GENERAL')

    def test_landing_page_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_200(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_location_detail_200(self):
        response = self.client.get(f'/location/{self.location.id}/')
        self.assertEqual(response.status_code, 200)

    def test_calculator_get_200(self):
        response = self.client.get('/calculator/')
        self.assertEqual(response.status_code, 200)

    def test_calculator_post_200(self):
        response = self.client.post('/calculator/', {
            'temperature_c': 35, 'humidity': 70,
        })
        self.assertEqual(response.status_code, 200)

    def test_alerts_list_200(self):
        response = self.client.get('/alerts/')
        self.assertEqual(response.status_code, 200)

    def test_safety_tips_200(self):
        response = self.client.get('/safety/')
        self.assertEqual(response.status_code, 200)

    def test_signup_200(self):
        response = self.client.get('/signup/')
        self.assertEqual(response.status_code, 200)

    def test_login_200(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    def test_subscriptions_requires_login(self):
        """Subscriptions should redirect unauthenticated users."""
        response = self.client.get('/subscriptions/')
        self.assertEqual(response.status_code, 302)

    def test_subscriptions_logged_in_200(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/subscriptions/')
        self.assertEqual(response.status_code, 200)

    def test_api_locations_json(self):
        response = self.client.get('/api/locations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_location_forecast_json(self):
        response = self.client.get(
            f'/api/locations/{self.location.id}/forecast/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_export_csv(self):
        response = self.client.get(f'/location/{self.location.id}/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_location_404(self):
        response = self.client.get('/location/99999/')
        self.assertEqual(response.status_code, 404)


# ══════════════════════════════════════════════
# Forecast Fetch Tests (Mocked API)
# ══════════════════════════════════════════════

class ForecastFetchTest(TestCase):
    """Test forecast fetching with mocked API responses."""

    def setUp(self):
        self.location = Location.objects.create(
            name='Delhi', latitude=28.6139, longitude=77.2090
        )

    @patch('warning.services.forecast.requests.get')
    def test_successful_fetch(self, mock_get):
        """Test that a successful API response creates forecast records."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'utc_offset_seconds': 19800,  # IST +5:30
            'hourly': {
                'time': [
                    '2024-05-01T00:00',
                    '2024-05-01T01:00',
                    '2024-05-01T02:00',
                ],
                'temperature_2m': [30.0, 31.0, 32.0],
                'relative_humidity_2m': [60.0, 55.0, 50.0],
            }
        }
        mock_get.return_value = mock_response

        from .services.forecast import fetch_forecast_for_location
        count = fetch_forecast_for_location(self.location)

        self.assertEqual(count, 3)
        self.assertEqual(ForecastRecord.objects.count(), 3)

    @patch('warning.services.forecast.requests.get')
    def test_network_error_returns_zero(self, mock_get):
        """Test graceful handling of network errors."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError('Fail')

        from .services.forecast import fetch_forecast_for_location
        count = fetch_forecast_for_location(self.location)

        self.assertEqual(count, 0)
        self.assertEqual(ForecastRecord.objects.count(), 0)

    @patch('warning.services.forecast.requests.get')
    def test_timeout_error_returns_zero(self, mock_get):
        """Test graceful handling of timeouts."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout('Timeout')

        from .services.forecast import fetch_forecast_for_location
        count = fetch_forecast_for_location(self.location)

        self.assertEqual(count, 0)
        self.assertEqual(ForecastRecord.objects.count(), 0)

    @patch('warning.services.forecast.requests.get')
    def test_update_or_create_no_duplicates(self, mock_get):
        """Running fetch twice with the same data should not create duplicates."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'utc_offset_seconds': 19800,
            'hourly': {
                'time': ['2024-05-01T00:00'],
                'temperature_2m': [30.0],
                'relative_humidity_2m': [60.0],
            }
        }
        mock_get.return_value = mock_response

        from .services.forecast import fetch_forecast_for_location
        fetch_forecast_for_location(self.location)
        fetch_forecast_for_location(self.location)

        self.assertEqual(ForecastRecord.objects.count(), 1)
