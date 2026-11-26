"""
Custom template tags and filters for HeatWatch.

Provides filters for consistent risk badge rendering across
all templates.
"""

from django import template
from warning.services.indices import SAFETY_ADVICE

register = template.Library()


@register.filter
def risk_badge_class(risk_level):
    """
    Return Bootstrap badge CSS class for a risk level.

    Usage in template:
        <span class="badge {{ alert.level|risk_badge_class }}">
    """
    mapping = {
        'NORMAL': 'bg-success',
        'CAUTION': 'bg-warning text-dark',
        'EXTREME_CAUTION': 'bg-warning',
        'DANGER': 'bg-danger',
        'EXTREME_DANGER': 'bg-dark',
    }
    return mapping.get(risk_level, 'bg-secondary')


@register.filter
def risk_display(risk_level):
    """
    Return human-readable display name for a risk level.

    Usage in template:
        {{ forecast.risk_level|risk_display }}
    """
    mapping = {
        'NORMAL': 'Normal',
        'CAUTION': 'Caution',
        'EXTREME_CAUTION': 'Extreme Caution',
        'DANGER': 'Danger',
        'EXTREME_DANGER': 'Extreme Danger',
    }
    return mapping.get(risk_level, risk_level)
