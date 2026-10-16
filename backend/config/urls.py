from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # The API has no HTML front page; send visitors to the interactive docs.
    path("", RedirectView.as_view(pattern_name="swagger-ui", permanent=False)),
    path("api/", include("apps.geo.urls")),
    path("api/", include("apps.trips.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
