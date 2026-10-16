from django.urls import path

from apps.trips import views

app_name = "trips"

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
]
