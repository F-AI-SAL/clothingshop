from django.urls import path
from .views_admin import admin_dashboard, webhook_test

urlpatterns = [
    path("", admin_dashboard, name="admin_dashboard"),
    path("webhook-test/", webhook_test, name="webhook_test"),
]
