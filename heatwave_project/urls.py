"""
URL configuration for heatwave_project.
Routes all app URLs through the warning app.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('warning.urls')),
]
