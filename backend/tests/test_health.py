import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_reports_ok(api_client: APIClient) -> None:
    response = api_client.get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_answers_platform_probes_with_unknown_hosts(api_client: APIClient) -> None:
    response = api_client.get("/api/health/", HTTP_HOST="10.0.4.7:10000")
    assert response.status_code == 200


def test_health_bypasses_https_redirect(api_client: APIClient, settings: object) -> None:
    settings.SECURE_SSL_REDIRECT = True  # type: ignore[attr-defined]
    assert api_client.get("/api/health/").status_code == 200


def test_health_keeps_cors_headers_for_browsers(api_client: APIClient) -> None:
    response = api_client.get("/api/health/", HTTP_ORIGIN="https://wtr-demo.vercel.app")
    assert response["Access-Control-Allow-Origin"] == "https://wtr-demo.vercel.app"


def test_other_routes_still_validate_host(api_client: APIClient) -> None:
    response = api_client.get("/api/docs/", HTTP_HOST="evil.example.com")
    assert response.status_code == 400
