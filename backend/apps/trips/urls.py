from django.urls import path

from apps.trips import views

app_name = "trips"

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("trips/", views.TripPlanCreateView.as_view(), name="trip-create"),
    path("trips/<uuid:plan_id>/", views.TripPlanDetailView.as_view(), name="trip-detail"),
    path("trips/<uuid:plan_id>/heatmap/", views.TripPlanHeatmapView.as_view(), name="trip-heatmap"),
]
