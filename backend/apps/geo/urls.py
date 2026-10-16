from django.urls import path

from apps.geo import views

app_name = "geo"

urlpatterns = [
    path("geocode/", views.GeocodeView.as_view(), name="geocode"),
]
