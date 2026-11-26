"""
Models for the HeatWatch warning application.

Defines the database schema for locations, forecast records,
alerts, subscriptions, user profiles, and cooling centers.
"""

from django.db import models
from django.contrib.auth.models import User


class Location(models.Model):
    """
    A geographic location being monitored for heatwave conditions.

    Each location has coordinates (lat/lon) and optional metadata
    like state/region and population notes.
    """
    name = models.CharField(max_length=100, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    state_region = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='State / Region'
    )
    population_note = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ForecastRecord(models.Model):
    """
    Hourly forecast data with computed thermal stress indices.

    Stores raw weather data alongside computed heat index,
    wet-bulb temperature, and classified risk level.
    unique_together on (location, timestamp) prevents duplicates.
    """
    RISK_CHOICES = [
        ('NORMAL', 'Normal'),
        ('CAUTION', 'Caution'),
        ('EXTREME_CAUTION', 'Extreme Caution'),
        ('DANGER', 'Danger'),
        ('EXTREME_DANGER', 'Extreme Danger'),
    ]

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='forecasts'
    )
    timestamp = models.DateTimeField()
    temperature_c = models.FloatField(help_text='Temperature in Celsius')
    humidity = models.FloatField(help_text='Relative humidity percentage')
    heat_index_c = models.FloatField(help_text='Computed heat index in Celsius')
    wet_bulb_c = models.FloatField(help_text='Wet-bulb temperature in Celsius')
    risk_level = models.CharField(
        max_length=20, choices=RISK_CHOICES, default='NORMAL'
    )

    class Meta:
        unique_together = ('location', 'timestamp')
        ordering = ['timestamp']

    def __str__(self):
        return (
            f"{self.location.name} @ {self.timestamp:%Y-%m-%d %H:%M}"
            f" - {self.risk_level}"
        )


class Alert(models.Model):
    """
    Heatwave alert for a location over a date range.

    Created when 3+ consecutive days of Danger-level heat index
    are detected in the forecast. Deactivated after the period passes.
    """
    LEVEL_CHOICES = ForecastRecord.RISK_CHOICES

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='alerts'
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    peak_heat_index = models.FloatField()
    message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.location.name}: {self.level}"
            f" ({self.start_date} to {self.end_date})"
        )


class Subscription(models.Model):
    """
    User subscription to alerts for a specific location.

    Users choose the minimum risk level they want to be notified about.
    unique_together on (user, location) prevents duplicate subscriptions.
    """
    MIN_LEVEL_CHOICES = ForecastRecord.RISK_CHOICES

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions'
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='subscriptions'
    )
    min_level = models.CharField(
        max_length=20, choices=MIN_LEVEL_CHOICES, default='DANGER',
        help_text='Minimum risk level to trigger notification'
    )

    class Meta:
        unique_together = ('user', 'location')

    def __str__(self):
        return f"{self.user.username} -> {self.location.name} (>={self.min_level})"


class UserProfile(models.Model):
    """
    Extended user profile with vulnerability group information.

    Vulnerable groups (Elderly, Outdoor Workers, Children) use
    stricter thresholds (3°C lower) for risk classification.
    """
    GROUP_CHOICES = [
        ('GENERAL', 'General Population'),
        ('ELDERLY', 'Elderly (65+)'),
        ('OUTDOOR_WORKER', 'Outdoor Worker'),
        ('CHILD', 'Child'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    group_type = models.CharField(
        max_length=20, choices=GROUP_CHOICES, default='GENERAL'
    )

    @property
    def is_vulnerable(self):
        """Returns True if the user belongs to a vulnerable group."""
        return self.group_type != 'GENERAL'

    def __str__(self):
        return f"{self.user.username} ({self.get_group_type_display()})"


class ShelterLocation(models.Model):
    """
    Cooling center / shelter for heat relief.

    These are shown on the map as blue markers so users can
    find the nearest place to cool down during a heatwave.
    """
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField(blank=True, default='')
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='shelters',
        help_text='Nearest monitored city'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (near {self.location.name})"
