"""
Heatwave detection and alert notification service for HeatWatch.

Scans forecast data to detect heatwave conditions (consecutive days
with dangerously high heat index) and notifies subscribed users.

A heatwave is defined as N or more consecutive days where the daily
maximum Heat Index reaches the configured threshold (default: 39°C
for 3 consecutive days).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Max
from django.utils import timezone

from warning.models import Location, ForecastRecord, Alert, Subscription
from warning.services.indices import classify_risk, get_safety_advice

logger = logging.getLogger(__name__)

# Configurable thresholds from settings.py
HEATWAVE_THRESHOLD = getattr(settings, 'HEATWAVE_THRESHOLD_C', 39.0)
HEATWAVE_MIN_DAYS = getattr(settings, 'HEATWAVE_MIN_DAYS', 3)

# Risk level ordering for comparison (higher number = more severe)
RISK_ORDER = {
    'NORMAL': 0,
    'CAUTION': 1,
    'EXTREME_CAUTION': 2,
    'DANGER': 3,
    'EXTREME_DANGER': 4,
}


def get_daily_max_heat_index(location):
    """
    Compute the daily maximum heat index for a location from forecast data.

    Groups hourly forecast records by date and finds the maximum
    heat index for each day.

    Args:
        location (Location): The location to analyze.

    Returns:
        list of dict: Each dict has 'date', 'max_hi', and 'risk_level'.
                      Sorted by date ascending.
    """
    forecasts = (
        ForecastRecord.objects
        .filter(location=location)
        .values('timestamp__date')
        .annotate(max_hi=Max('heat_index_c'))
        .order_by('timestamp__date')
    )

    daily = []
    for entry in forecasts:
        risk = classify_risk(entry['max_hi'])
        daily.append({
            'date': entry['timestamp__date'],
            'max_hi': entry['max_hi'],
            'risk_level': risk,
        })
    return daily


def detect_heatwave_runs(daily_data, threshold=None, min_days=None):
    """
    Detect all runs of consecutive days where daily max heat index >= threshold.

    A heatwave is defined as 'min_days' or more consecutive days
    meeting the threshold condition.

    Args:
        daily_data (list): Output of get_daily_max_heat_index().
        threshold (float): Heat index threshold in °C (default from settings).
        min_days (int): Minimum consecutive days (default from settings).

    Returns:
        list of dict: Each dict has 'start_date', 'end_date', 'peak_hi',
                       'days', and 'peak_risk'.
    """
    if threshold is None:
        threshold = HEATWAVE_THRESHOLD
    if min_days is None:
        min_days = HEATWAVE_MIN_DAYS

    runs = []
    current_run = []

    for day in daily_data:
        if day['max_hi'] >= threshold:
            # This day qualifies — extend the current run
            current_run.append(day)
        else:
            # Day below threshold — check if the run we just ended qualifies
            if len(current_run) >= min_days:
                peak = max(current_run, key=lambda d: d['max_hi'])
                runs.append({
                    'start_date': current_run[0]['date'],
                    'end_date': current_run[-1]['date'],
                    'peak_hi': peak['max_hi'],
                    'days': len(current_run),
                    'peak_risk': classify_risk(peak['max_hi']),
                })
            current_run = []

    # Check if the last run qualifies (data may end during a heatwave)
    if len(current_run) >= min_days:
        peak = max(current_run, key=lambda d: d['max_hi'])
        runs.append({
            'start_date': current_run[0]['date'],
            'end_date': current_run[-1]['date'],
            'peak_hi': peak['max_hi'],
            'days': len(current_run),
            'peak_risk': classify_risk(peak['max_hi']),
        })

    return runs


def create_alerts_for_location(location):
    """
    Detect heatwaves for a location and create Alert records.

    - Deactivates old alerts whose end_date has passed.
    - Creates new alerts without duplicates (same location + start_date).
    - Returns a list of newly created Alert objects.

    Args:
        location (Location): The location to check.

    Returns:
        list[Alert]: Newly created Alert objects.
    """
    today = timezone.now().date()

    # Deactivate expired alerts
    Alert.objects.filter(
        location=location,
        end_date__lt=today,
        is_active=True
    ).update(is_active=False)

    # Get daily data and detect heatwave runs
    daily_data = get_daily_max_heat_index(location)
    runs = detect_heatwave_runs(daily_data)

    new_alerts = []
    for run in runs:
        advice = get_safety_advice(run['peak_risk'])

        # Build a human-readable alert message with safety tips
        message = (
            f"Heatwave Alert for {location.name}!\n\n"
            f"A heatwave of {run['days']} consecutive days is forecast "
            f"from {run['start_date']} to {run['end_date']}.\n"
            f"Peak Heat Index: {run['peak_hi']:.1f}°C "
            f"({advice['title']})\n\n"
            f"Safety Tips:\n"
        )
        for tip in advice['advice']:
            message += f"  • {tip}\n"

        # Create alert only if it doesn't already exist for this date
        alert, created = Alert.objects.get_or_create(
            location=location,
            start_date=run['start_date'],
            defaults={
                'level': run['peak_risk'],
                'end_date': run['end_date'],
                'peak_heat_index': run['peak_hi'],
                'message': message,
                'is_active': True,
            }
        )
        if created:
            new_alerts.append(alert)
            logger.info(
                "Created alert for %s: %s to %s",
                location.name, run['start_date'], run['end_date']
            )

    return new_alerts


def notify_subscribers(alert):
    """
    Send email notification to all subscribers for a given alert.

    Only notifies subscribers whose min_level is at or below
    the alert's severity level.

    Args:
        alert (Alert): The alert to notify about.
    """
    alert_level_order = RISK_ORDER.get(alert.level, 0)

    # Get all subscriptions for this location
    subscriptions = Subscription.objects.filter(
        location=alert.location
    ).select_related('user')

    for sub in subscriptions:
        sub_level_order = RISK_ORDER.get(sub.min_level, 0)

        # Only notify if the alert level meets the subscriber's threshold
        if alert_level_order >= sub_level_order:
            try:
                send_mail(
                    subject=(
                        f"🔥 HeatWatch Alert: {alert.level} "
                        f"for {alert.location.name}"
                    ),
                    message=alert.message,
                    from_email='heatwatch@example.com',
                    recipient_list=[sub.user.email],
                    fail_silently=False,
                )
                logger.info(
                    "Notified %s about alert in %s",
                    sub.user.username, alert.location.name
                )
            except Exception as e:
                logger.error(
                    "Failed to email %s: %s", sub.user.username, e
                )


def process_all_alerts(location_name=None):
    """
    Create alerts and notify subscribers for all (or one) location(s).

    Args:
        location_name (str, optional): Filter to a single location
            (case-insensitive partial match).

    Returns:
        dict: Summary with 'alerts_created' and 'locations_processed'.
    """
    if location_name:
        locations = Location.objects.filter(name__icontains=location_name)
    else:
        locations = Location.objects.all()

    summary = {'alerts_created': 0, 'locations_processed': 0}

    for loc in locations:
        new_alerts = create_alerts_for_location(loc)
        for alert in new_alerts:
            notify_subscribers(alert)
        summary['alerts_created'] += len(new_alerts)
        summary['locations_processed'] += 1

    return summary
