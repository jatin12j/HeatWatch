"""
Views for the HeatWatch warning application.

Implements the dashboard, location detail, calculator, alerts,
subscriptions, authentication, safety tips, CSV export, JSON API,
and staff-only data refresh functionality.
"""

import csv

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Location, ForecastRecord, Alert, Subscription,
    UserProfile, ShelterLocation
)
from .forms import (
    HeatIndexCalculatorForm, SignUpForm, SubscriptionForm, AlertFilterForm
)
from .services.indices import (
    compute_heat_index, compute_wet_bulb, classify_risk,
    get_safety_advice, get_risk_color, SAFETY_ADVICE
)


# ══════════════════════════════════════════════
# Landing Page / Front Gateway
# ══════════════════════════════════════════════

def landing_page(request):
    """
    Creative front page / landing gateway for HeatWatch.

    Explains the system's purpose, thermal biometeorology science,
    key features, and provides a direct gateway to Sign In, Sign Up,
    or explore the Live Dashboard.
    """
    total_locations = Location.objects.count()
    active_alerts_count = Alert.objects.filter(is_active=True).count()
    shelters_count = ShelterLocation.objects.count()
    preview_cities = Location.objects.all()[:6]

    context = {
        'total_locations': total_locations,
        'active_alerts_count': active_alerts_count,
        'shelters_count': shelters_count,
        'preview_cities': preview_cities,
    }
    return render(request, 'warning/landing.html', context)


# ══════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════

def dashboard(request):
    """
    Main dashboard view with an interactive map and risk summary.

    Shows a Leaflet map with color-coded markers for each location,
    summary cards with risk level counts, and active alerts.
    """
    locations = Location.objects.all()

    # Build location data for the JavaScript map
    map_data = []
    risk_counts = {
        'NORMAL': 0, 'CAUTION': 0, 'EXTREME_CAUTION': 0,
        'DANGER': 0, 'EXTREME_DANGER': 0
    }

    for loc in locations:
        # Get peak heat index and max temperature across all forecast records for this location
        agg = ForecastRecord.objects.filter(
            location=loc
        ).aggregate(
            peak_hi=Max('heat_index_c'),
            max_temp=Max('temperature_c')
        )

        peak_hi = agg['peak_hi']
        max_temp = agg['max_temp']
        if peak_hi is not None:
            risk = classify_risk(peak_hi)
            color = get_risk_color(risk)
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        else:
            risk = 'NORMAL'
            color = get_risk_color('NORMAL')
            peak_hi = 0
            max_temp = 0

        map_data.append({
            'id': loc.id,
            'name': loc.name,
            'lat': loc.latitude,
            'lon': loc.longitude,
            'peak_hi': round(peak_hi, 1) if peak_hi else 0,
            'max_temp': round(max_temp, 1) if max_temp else 0,
            'risk': risk,
            'color': color,
            'state': loc.state_region,
        })

    # Get shelter data for the cooling centers layer
    shelters = ShelterLocation.objects.all().select_related('location')
    shelter_data = [{
        'name': s.name,
        'lat': s.latitude,
        'lon': s.longitude,
        'address': s.address,
        'city': s.location.name,
    } for s in shelters]

    # Active alerts (most recent 10)
    active_alerts = (
        Alert.objects.filter(is_active=True)
        .select_related('location')[:10]
    )

    context = {
        'map_data': map_data,
        'map_data_json': map_data,
        'shelter_data': shelter_data,
        'shelter_data_json': shelter_data,
        'risk_counts': risk_counts,
        'active_alerts': active_alerts,
        'total_locations': locations.count(),
        'total_active_alerts': Alert.objects.filter(is_active=True).count(),
        'has_forecast_data': ForecastRecord.objects.exists(),
    }
    return render(request, 'warning/dashboard.html', context)


# ══════════════════════════════════════════════
# Location Detail
# ══════════════════════════════════════════════

def location_detail(request, pk):
    """
    Detailed view for a single location with charts and forecast data.

    Shows current conditions, 7-day chart, daily summary table,
    safety advice, and subscription controls.
    """
    location = get_object_or_404(Location, pk=pk)
    forecasts = ForecastRecord.objects.filter(
        location=location
    ).order_by('timestamp')

    # Build chart data arrays for Chart.js
    chart_labels = []
    temp_data = []
    hi_data = []
    wb_data = []

    for f in forecasts:
        local_dt = timezone.localtime(f.timestamp)
        chart_labels.append(local_dt.strftime('%b %d %H:%M'))
        temp_data.append(f.temperature_c)
        hi_data.append(f.heat_index_c)
        wb_data.append(f.wet_bulb_c)

    # Build daily summary (group hourly records by local date)
    daily_summary = []
    current_date = None
    day_records = []

    for f in forecasts:
        f_date = timezone.localtime(f.timestamp).date()
        if f_date != current_date:
            if day_records:
                # Process the previous day
                max_temp = max(r.temperature_c for r in day_records)
                max_hi = max(r.heat_index_c for r in day_records)
                risk = classify_risk(max_hi)
                daily_summary.append({
                    'date': current_date,
                    'max_temp': round(max_temp, 1),
                    'max_hi': round(max_hi, 1),
                    'risk': risk,
                    'advice': get_safety_advice(risk),
                })
            current_date = f_date
            day_records = [f]
        else:
            day_records.append(f)

    # Don't forget the last day
    if day_records:
        max_temp = max(r.temperature_c for r in day_records)
        max_hi = max(r.heat_index_c for r in day_records)
        risk = classify_risk(max_hi)
        daily_summary.append({
            'date': current_date,
            'max_temp': round(max_temp, 1),
            'max_hi': round(max_hi, 1),
            'risk': risk,
            'advice': get_safety_advice(risk),
        })

    # Peak values across all forecast data
    peak_hi = max(hi_data) if hi_data else 0
    peak_risk = classify_risk(peak_hi) if hi_data else 'NORMAL'
    peak_advice = get_safety_advice(peak_risk)

    # Latest forecast record (current conditions)
    latest = forecasts.last()

    # Check if logged-in user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = Subscription.objects.filter(
            user=request.user, location=location
        ).exists()

    # Active alerts for this location
    alerts = Alert.objects.filter(location=location, is_active=True)

    context = {
        'location': location,
        'chart_labels': chart_labels,
        'chart_labels_json': chart_labels,
        'temp_data': temp_data,
        'temp_data_json': temp_data,
        'hi_data': hi_data,
        'hi_data_json': hi_data,
        'wb_data': wb_data,
        'wb_data_json': wb_data,
        'daily_summary': daily_summary,
        'peak_hi': round(peak_hi, 1),
        'peak_risk': peak_risk,
        'peak_advice': peak_advice,
        'latest': latest,
        'is_subscribed': is_subscribed,
        'alerts': alerts,
        'has_data': len(chart_labels) > 0,
    }
    return render(request, 'warning/location_detail.html', context)


# ══════════════════════════════════════════════
# Heat Risk Calculator
# ══════════════════════════════════════════════

def calculator(request):
    """
    Interactive heat risk calculator.

    User enters temperature and humidity to see computed heat index,
    wet-bulb temperature, risk level, and safety advice.
    Demonstrates Django Forms (GET/POST) and CSRF protection.
    """
    result = None

    if request.method == 'POST':
        form = HeatIndexCalculatorForm(request.POST)
        if form.is_valid():
            temp_c = form.cleaned_data['temperature_c']
            humidity = form.cleaned_data['humidity']
            vulnerable = form.cleaned_data['vulnerable']

            # Compute thermal indices
            hi = compute_heat_index(temp_c, humidity)
            wb = compute_wet_bulb(temp_c, humidity)
            risk = classify_risk(hi, vulnerable=vulnerable)
            advice = get_safety_advice(risk)

            result = {
                'heat_index': hi,
                'wet_bulb': wb,
                'risk_level': risk,
                'advice': advice,
                'temperature_c': temp_c,
                'humidity': humidity,
                'vulnerable': vulnerable,
            }
    else:
        form = HeatIndexCalculatorForm()

    return render(request, 'warning/calculator.html', {
        'form': form,
        'result': result,
    })


# ══════════════════════════════════════════════
# Alerts
# ══════════════════════════════════════════════

def alerts_list(request):
    """
    Paginated list of all alerts with optional filters.

    Supports filtering by location, risk level, and date range.
    """
    form = AlertFilterForm(request.GET)
    alerts = Alert.objects.all().select_related('location')

    # Apply filters if the form is valid
    if form.is_valid():
        if form.cleaned_data.get('location'):
            alerts = alerts.filter(
                location_id=form.cleaned_data['location']
            )
        if form.cleaned_data.get('level'):
            alerts = alerts.filter(level=form.cleaned_data['level'])
        if form.cleaned_data.get('date_from'):
            alerts = alerts.filter(
                start_date__gte=form.cleaned_data['date_from']
            )
        if form.cleaned_data.get('date_to'):
            alerts = alerts.filter(
                end_date__lte=form.cleaned_data['date_to']
            )

    # Paginate results (10 per page)
    paginator = Paginator(alerts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # All locations for the filter dropdown
    locations = Location.objects.all()

    return render(request, 'warning/alerts_list.html', {
        'page_obj': page_obj,
        'form': form,
        'locations': locations,
    })


# ══════════════════════════════════════════════
# Authentication
# ══════════════════════════════════════════════

def signup_view(request):
    """
    User registration view with group type selection.

    Creates a User and associated UserProfile, then logs in
    and redirects to the dashboard with a welcome message.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create UserProfile with the selected group type
            UserProfile.objects.create(
                user=user,
                group_type=form.cleaned_data['group_type']
            )
            login(request, user)
            messages.success(
                request,
                f'Welcome, {user.username}! Your account has been created.'
            )
            return redirect('dashboard')
    else:
        form = SignUpForm()

    return render(request, 'warning/signup.html', {'form': form})


# ══════════════════════════════════════════════
# Subscriptions
# ══════════════════════════════════════════════

@login_required
def subscriptions_view(request):
    """
    Manage user subscriptions: view, add, and remove.

    Logged-in users can subscribe to locations and choose the
    minimum alert level they want to be notified about.
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            form = SubscriptionForm(request.POST)
            if form.is_valid():
                location = form.cleaned_data['location']
                min_level = form.cleaned_data['min_level']
                sub, created = Subscription.objects.update_or_create(
                    user=request.user,
                    location=location,
                    defaults={'min_level': min_level},
                )
                if created:
                    messages.success(
                        request, f'Subscribed to {sub.location.name}!'
                    )
                else:
                    messages.info(
                        request,
                        f'Updated alert threshold for {sub.location.name} to {sub.get_min_level_display()}.'
                    )
                return redirect('subscriptions')

        elif action == 'remove':
            sub_id = request.POST.get('subscription_id')
            Subscription.objects.filter(
                id=sub_id, user=request.user
            ).delete()
            messages.success(request, 'Subscription removed.')
            return redirect('subscriptions')

    subs = Subscription.objects.filter(
        user=request.user
    ).select_related('location')
    form = SubscriptionForm()

    return render(request, 'warning/subscriptions.html', {
        'subscriptions': subs,
        'form': form,
    })


@login_required
@require_POST
def subscribe_location(request, pk):
    """Quick subscribe to a location from its detail page."""
    location = get_object_or_404(Location, pk=pk)

    _, created = Subscription.objects.get_or_create(
        user=request.user,
        location=location,
        defaults={'min_level': 'DANGER'}
    )

    if created:
        messages.success(
            request, f'Subscribed to alerts for {location.name}!'
        )
    else:
        messages.info(
            request, f'You are already subscribed to {location.name}.'
        )

    return redirect('location_detail', pk=pk)


@login_required
@require_POST
def unsubscribe_location(request, pk):
    """Unsubscribe from a location from its detail page."""
    location = get_object_or_404(Location, pk=pk)
    deleted, _ = Subscription.objects.filter(
        user=request.user, location=location
    ).delete()

    if deleted:
        messages.success(request, f'Unsubscribed from {location.name}.')

    return redirect('location_detail', pk=pk)


# ══════════════════════════════════════════════
# Safety Tips
# ══════════════════════════════════════════════

def safety_tips(request):
    """Static safety tips page organized by risk level."""
    return render(request, 'warning/safety.html', {
        'safety_data': SAFETY_ADVICE,
    })


# ══════════════════════════════════════════════
# CSV Export
# ══════════════════════════════════════════════

def export_csv(request, pk):
    """
    Export forecast data for a location as a downloadable CSV file.

    Demonstrates Django HttpResponse with custom content type.
    """
    location = get_object_or_404(Location, pk=pk)
    forecasts = ForecastRecord.objects.filter(
        location=location
    ).order_by('timestamp')

    # Create CSV response with appropriate headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{location.name}_forecast.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'Temperature (°C)', 'Humidity (%)',
        'Heat Index (°C)', 'Wet-Bulb (°C)', 'Risk Level'
    ])

    for f in forecasts:
        writer.writerow([
            f.timestamp.strftime('%Y-%m-%d %H:%M'),
            f.temperature_c, f.humidity,
            f.heat_index_c, f.wet_bulb_c,
            f.risk_level,
        ])

    return response


# ══════════════════════════════════════════════
# JSON API Endpoints
# ══════════════════════════════════════════════

def api_locations(request):
    """
    JSON API: list all locations with their peak risk.

    Returns a JSON response with location data — no DRF needed,
    just Django's built-in JsonResponse.
    """
    locations = Location.objects.all()
    data = []
    for loc in locations:
        peak = ForecastRecord.objects.filter(
            location=loc
        ).aggregate(peak_hi=Max('heat_index_c'))

        peak_hi = peak['peak_hi'] or 0
        data.append({
            'id': loc.id,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'state_region': loc.state_region,
            'peak_heat_index': round(peak_hi, 1),
            'peak_risk': classify_risk(peak_hi) if peak_hi else 'NORMAL',
        })

    return JsonResponse({'locations': data})


def api_location_forecast(request, pk):
    """JSON API: forecast data for a single location."""
    location = get_object_or_404(Location, pk=pk)
    forecasts = ForecastRecord.objects.filter(
        location=location
    ).order_by('timestamp')

    data = {
        'location': {
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
        },
        'forecasts': [
            {
                'timestamp': f.timestamp.isoformat(),
                'temperature_c': f.temperature_c,
                'humidity': f.humidity,
                'heat_index_c': f.heat_index_c,
                'wet_bulb_c': f.wet_bulb_c,
                'risk_level': f.risk_level,
            }
            for f in forecasts
        ],
    }

    return JsonResponse(data)


# ══════════════════════════════════════════════
# Staff-Only Actions
# ══════════════════════════════════════════════

@staff_member_required
@require_POST
def refresh_data(request):
    """
    Staff-only view to trigger a forecast data refresh.

    Fetches fresh data from Open-Meteo and processes alerts.
    Only accessible by staff users via POST request.
    """
    from .services.forecast import fetch_all_forecasts
    from .services.alerts import process_all_alerts

    fetch_summary = fetch_all_forecasts()
    alert_summary = process_all_alerts()

    messages.success(
        request,
        f'Data refreshed! {fetch_summary["total_records"]} records updated, '
        f'{alert_summary["alerts_created"]} new alerts created.'
    )
    return redirect('dashboard')
