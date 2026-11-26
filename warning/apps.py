"""App configuration for the HeatWatch warning system."""
from django.apps import AppConfig


class WarningConfig(AppConfig):
    """Configuration for the warning (HeatWatch) application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'warning'
    verbose_name = 'HeatWatch Warning System'
