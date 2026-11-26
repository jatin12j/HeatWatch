"""
Forms for the HeatWatch warning application.

Includes forms for the heat risk calculator, user signup,
alert subscriptions, and alert filtering.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Subscription, UserProfile


class HeatIndexCalculatorForm(forms.Form):
    """
    Form for the interactive heat risk calculator.

    Users enter temperature and humidity to compute heat index,
    wet-bulb temperature, and risk classification.
    """
    temperature_c = forms.FloatField(
        label='Temperature (°C)',
        min_value=-50, max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 40',
            'step': '0.1',
        })
    )
    humidity = forms.FloatField(
        label='Relative Humidity (%)',
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 60',
            'step': '1',
        })
    )
    vulnerable = forms.BooleanField(
        required=False,
        label='Vulnerable group (Elderly, Child, Outdoor Worker)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class SignUpForm(UserCreationForm):
    """
    User registration form with group type selection.

    Extends Django's UserCreationForm to include email and
    vulnerability group type for personalized risk thresholds.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
        })
    )
    group_type = forms.ChoiceField(
        choices=UserProfile.GROUP_CHOICES,
        label='Group Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name in ('username', 'password1', 'password2'):
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control'
            })


class SubscriptionForm(forms.ModelForm):
    """
    Form to subscribe to a location's alerts.

    Users select a location and the minimum risk level they
    want to be notified about.
    """
    class Meta:
        model = Subscription
        fields = ('location', 'min_level')
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select'}),
            'min_level': forms.Select(attrs={'class': 'form-select'}),
        }


class AlertFilterForm(forms.Form):
    """
    Form for filtering alerts on the history page.

    Supports filtering by location, risk level, and date range.
    """
    location = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Levels')] + list(Subscription.MIN_LEVEL_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        label='From',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    date_to = forms.DateField(
        required=False,
        label='To',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
