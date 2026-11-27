"""URL configuration for the HeatWatch warning app."""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ── Landing / Front Page Gateway ──
    path('', views.landing_page, name='landing'),

    # ── Dashboard ──
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Location detail and actions ──
    path('location/<int:pk>/', views.location_detail, name='location_detail'),
    path('location/<int:pk>/subscribe/', views.subscribe_location,
         name='subscribe_location'),
    path('location/<int:pk>/unsubscribe/', views.unsubscribe_location,
         name='unsubscribe_location'),
    path('location/<int:pk>/export/', views.export_csv, name='export_csv'),

    # ── Calculator ──
    path('calculator/', views.calculator, name='calculator'),

    # ── Alerts ──
    path('alerts/', views.alerts_list, name='alerts_list'),

    # ── Subscriptions ──
    path('subscriptions/', views.subscriptions_view, name='subscriptions'),

    # ── Safety tips ──
    path('safety/', views.safety_tips, name='safety_tips'),

    # ── Authentication ──
    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(
        template_name='warning/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ── Staff actions ──
    path('refresh/', views.refresh_data, name='refresh_data'),

    # ── JSON API ──
    path('api/locations/', views.api_locations, name='api_locations'),
    path('api/locations/<int:pk>/forecast/', views.api_location_forecast,
         name='api_location_forecast'),
]
