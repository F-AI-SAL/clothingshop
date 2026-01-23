from django.urls import path
from .views_admin import admin_dashboard

urlpatterns = [
    path("", admin_dashboard, name="admin_dashboard"),
]
