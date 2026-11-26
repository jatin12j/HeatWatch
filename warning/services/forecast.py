"""
Forecast data fetching service for HeatWatch.

Fetches hourly forecast data from the Open-Meteo API for each
monitored location and stores it with computed thermal indices.

Open-Meteo API: https://api.open-meteo.com/v1/forecast
No API key required — completely free for non-commercial use.
"""

import logging
import time
from datetime import datetime, timedelta, timezone as dt_timezone

import requests
from django.conf import settings

from warning.models import Location, ForecastRecord
from warning.services.indices import compute_heat_index, compute_wet_bulb, classify_risk

logger = logging.getLogger(__name__)

# Open-Meteo API base URL (no key required)
API_URL = getattr(
    settings, 'OPEN_METEO_BASE_URL',
    'https://api.open-meteo.com/v1/forecast'
)


def fetch_forecast_for_location(location):
    """
    Fetch 7-day hourly forecast from Open-Meteo for a single location.

    Requests temperature_2m and relative_humidity_2m, computes heat index
    and wet-bulb temperature, classifies risk, and stores using
    update_or_create to prevent duplicates.

    Args:
        location (Location): The location model instance.

    Returns:
        int: Number of forecast records created or updated.
    """
    params = {
        'latitude': location.latitude,
        'longitude': location.longitude,
        'hourly': 'temperature_2m,relative_humidity_2m',
        'forecast_days': 7,
        'timezone': 'auto',
    }

    # --- Make the API request with error handling ---
    try:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching forecast for %s", location.name)
        return 0
    except requests.exceptions.SSLError:
        # Fallback for environments with self-signed proxy/Wi-Fi SSL interception
        try:
            response = requests.get(API_URL, params=params, timeout=30, verify=False)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Network error fetching forecast for %s: %s", location.name, e)
            return 0
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching forecast for %s: %s", location.name, e)
        return 0
    except ValueError as e:
        logger.error("Invalid JSON response for %s: %s", location.name, e)
        return 0

    # --- Parse the response ---
    hourly = data.get('hourly', {})
    timestamps = hourly.get('time', [])
    temperatures = hourly.get('temperature_2m', [])
    humidities = hourly.get('relative_humidity_2m', [])

    if not timestamps:
        logger.warning("No hourly data received for %s", location.name)
        return 0

    # Build a timezone offset from the response's utc_offset_seconds
    utc_offset_seconds = data.get('utc_offset_seconds', 0)
    tz_offset = dt_timezone(timedelta(seconds=utc_offset_seconds))

    count = 0
    for i, ts_str in enumerate(timestamps):
        # Skip if temperature or humidity is None (missing data)
        temp = temperatures[i] if i < len(temperatures) else None
        rh = humidities[i] if i < len(humidities) else None

        if temp is None or rh is None:
            continue

        # Parse the ISO timestamp and make it timezone-aware
        try:
            naive_dt = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M')
            aware_dt = naive_dt.replace(tzinfo=tz_offset)
        except (ValueError, TypeError) as e:
            logger.warning("Bad timestamp '%s' for %s: %s", ts_str, location.name, e)
            continue

        # Compute thermal indices
        hi = compute_heat_index(temp, rh)
        wb = compute_wet_bulb(temp, rh)
        risk = classify_risk(hi)

        # Store in database (update if exists, create if not)
        ForecastRecord.objects.update_or_create(
            location=location,
            timestamp=aware_dt,
            defaults={
                'temperature_c': round(temp, 1),
                'humidity': round(rh, 1),
                'heat_index_c': hi,
                'wet_bulb_c': wb,
                'risk_level': risk,
            }
        )
        count += 1

    logger.info("Stored %d forecast records for %s", count, location.name)
    return count


def fetch_all_forecasts(location_name=None):
    """
    Fetch forecasts for all locations, or a single one by name.

    Processes each location independently so one failure does not
    block the others.

    Args:
        location_name (str, optional): If given, only fetch for
            locations matching this name (case-insensitive partial match).

    Returns:
        dict: Summary with 'total_records', 'locations_processed', 'errors'.
    """
    if location_name:
        locations = Location.objects.filter(name__icontains=location_name)
    else:
        locations = Location.objects.all()

    summary = {
        'total_records': 0,
        'locations_processed': 0,
        'errors': [],
    }

    for loc in locations:
        try:
            count = fetch_forecast_for_location(loc)
            summary['total_records'] += count
            summary['locations_processed'] += 1
            if count == 0:
                summary['errors'].append(f"{loc.name}: No data fetched")
            time.sleep(0.25)
        except Exception as e:
            logger.error("Unexpected error for %s: %s", loc.name, e)
            summary['errors'].append(f"{loc.name}: {str(e)}")

    return summary
