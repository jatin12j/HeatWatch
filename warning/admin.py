"""
Admin configuration for the HeatWatch warning application.

Registers all models with customized list displays, filters,
and search fields for easy data management.
"""

from django.contrib import admin
from .models import (
    Location, ForecastRecord, Alert,
    Subscription, UserProfile, ShelterLocation
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin view for monitored locations."""
    list_display = ('name', 'latitude', 'longitude', 'state_region')
    search_fields = ('name', 'state_region')
    list_filter = ('state_region',)


@admin.register(ForecastRecord)
class ForecastRecordAdmin(admin.ModelAdmin):
    """Admin view for hourly forecast records."""
    list_display = (
        'location', 'timestamp', 'temperature_c', 'humidity',
        'heat_index_c', 'wet_bulb_c', 'risk_level'
    )
    list_filter = ('risk_level', 'location')
    search_fields = ('location__name',)
    date_hierarchy = 'timestamp'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin view for heatwave alerts."""
    list_display = (
        'location', 'level', 'start_date', 'end_date',
        'peak_heat_index', 'is_active', 'created_at'
    )
    list_filter = ('level', 'is_active', 'location')
    search_fields = ('location__name', 'message')
    date_hierarchy = 'start_date'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin view for user alert subscriptions."""
    list_display = ('user', 'location', 'min_level')
    list_filter = ('min_level', 'location')
    search_fields = ('user__username', 'location__name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin view for extended user profiles."""
    list_display = ('user', 'group_type')
    list_filter = ('group_type',)
    search_fields = ('user__username',)


@admin.register(ShelterLocation)
class ShelterLocationAdmin(admin.ModelAdmin):
    """Admin view for cooling centers."""
    list_display = ('name', 'latitude', 'longitude', 'location', 'address')
    search_fields = ('name', 'address', 'location__name')
    list_filter = ('location',)
