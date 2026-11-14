import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.urls import reverse
from rest_framework.test import APIClient

SERVICE_NAME = "student-management-api"


@pytest.fixture
def api_client():
    return APIClient()


def test_health_returns_liveness_without_querying_database(api_client):
    with patch("apps.common.views.connection.cursor") as cursor:
        response = api_client.get(reverse("common:health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": SERVICE_NAME}
    cursor.assert_not_called()


@pytest.mark.django_db
def test_readiness_returns_success_when_database_is_available(api_client):
    response = api_client.get(reverse("common:readiness"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": SERVICE_NAME}


def test_readiness_returns_service_unavailable_when_database_fails(api_client):
    with patch(
        "apps.common.views.connection.cursor",
        side_effect=DatabaseError("database unavailable"),
    ):
        response = api_client.get(reverse("common:readiness"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "service": SERVICE_NAME,
    }


@pytest.mark.django_db
def test_openapi_schema_is_admin_protected_and_contains_health_routes(api_client):
    response = api_client.get(reverse("schema"))

    assert response.status_code == 403

    user = get_user_model().objects.create_user(
        email="admin@example.com",
        password="secure-pass",
        is_staff=True,
    )
    api_client.force_authenticate(user=user)
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    schema = json.loads(response.content)
    assert "/api/v1/health/" in schema["paths"]
    assert "/api/v1/health/ready/" in schema["paths"]
