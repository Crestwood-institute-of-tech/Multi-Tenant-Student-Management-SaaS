import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.institutions.models import (
    Institution,
    InstitutionProvisioningRequest,
    Membership,
)
from apps.institutions.services import create_institution_provisioning_request

User = get_user_model()

REQUESTS_URL = reverse("institution_provisioning:request-list")


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def create_user(email):
    return User.objects.create_user(email=email, password="secure-pass")


def request_details(proposed_owner):
    return {
        "institution_name": "North Academy",
        "institution_slug": "North-Academy",
        "proposed_owner": str(proposed_owner.pk),
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", REQUESTS_URL),
        ("post", REQUESTS_URL),
        ("get", f"{REQUESTS_URL}{uuid.uuid4()}/"),
    ],
)
def test_provisioning_endpoints_require_authentication(method, url):
    response = getattr(APIClient(), method)(url, data={}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_authenticated_submission_uses_session_requester_and_service():
    requester = create_user("requester@example.com")
    proposed_owner = create_user("owner@example.com")
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.post(REQUESTS_URL, request_details(proposed_owner), format="json")

    assert response.status_code == 201
    created = InstitutionProvisioningRequest.objects.get()
    assert created.requesting_user == requester
    assert created.proposed_owner == proposed_owner
    assert created.institution_name == "North Academy"
    assert created.institution_slug == "north-academy"
    assert created.status == InstitutionProvisioningRequest.Status.PENDING
    assert response.data == {
        "id": str(created.pk),
        "institution_name": "North Academy",
        "institution_slug": "north-academy",
        "proposed_owner": str(proposed_owner.pk),
        "status": InstitutionProvisioningRequest.Status.PENDING,
        "created_at": created.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": created.updated_at.isoformat().replace("+00:00", "Z"),
    }
    assert Institution.objects.count() == 0
    assert Membership.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "invalid_field"),
    [
        ({"institution_name": "   "}, "institution_name"),
        ({"institution_slug": "Not a canonical slug"}, "institution_slug"),
        ({"proposed_owner": str(uuid.uuid4())}, "proposed_owner"),
    ],
)
def test_submission_validates_writable_fields(overrides, invalid_field):
    requester = create_user("requester@example.com")
    proposed_owner = create_user("owner@example.com")
    payload = request_details(proposed_owner)
    payload.update(overrides)
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.post(REQUESTS_URL, payload, format="json")

    assert response.status_code == 400
    assert invalid_field in response.data
    assert InstitutionProvisioningRequest.objects.count() == 0


@pytest.mark.django_db
def test_submission_rejects_client_supplied_requester_identity():
    requester = create_user("requester@example.com")
    forged_requester = create_user("forged@example.com")
    payload = request_details(requester)
    payload["requesting_user"] = str(forged_requester.pk)
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.post(REQUESTS_URL, payload, format="json")

    assert response.status_code == 400
    assert "requesting_user" in response.data
    assert InstitutionProvisioningRequest.objects.count() == 0


@pytest.mark.django_db
def test_request_history_is_scoped_to_authenticated_requester():
    requester = create_user("requester@example.com")
    other_requester = create_user("other@example.com")
    owned_request = create_institution_provisioning_request(
        requesting_user=requester,
        proposed_owner=requester,
        institution_name="North Academy",
        institution_slug="north-academy",
    )
    create_institution_provisioning_request(
        requesting_user=other_requester,
        proposed_owner=other_requester,
        institution_name="South Academy",
        institution_slug="south-academy",
    )
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.get(REQUESTS_URL)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert [item["id"] for item in response.data["results"]] == [str(owned_request.pk)]


@pytest.mark.django_db
def test_request_detail_is_scoped_and_unknown_requests_return_404():
    requester = create_user("requester@example.com")
    other_requester = create_user("other@example.com")
    other_request = create_institution_provisioning_request(
        requesting_user=other_requester,
        proposed_owner=other_requester,
        institution_name="South Academy",
        institution_slug="south-academy",
    )
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.get(f"{REQUESTS_URL}{other_request.pk}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_request_detail_returns_owned_request_and_malformed_uuid_is_not_found():
    requester = create_user("requester@example.com")
    created = create_institution_provisioning_request(
        requesting_user=requester,
        proposed_owner=requester,
        institution_name="North Academy",
        institution_slug="north-academy",
    )
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.get(f"{REQUESTS_URL}{created.pk}/")
    malformed_uuid_response = client.get(f"{REQUESTS_URL}not-a-uuid/")

    assert response.status_code == 200
    assert response.data["id"] == str(created.pk)
    assert malformed_uuid_response.status_code == 404


@pytest.mark.django_db
def test_request_history_uses_page_number_pagination():
    requester = create_user("requester@example.com")
    for index in range(21):
        create_institution_provisioning_request(
            requesting_user=requester,
            proposed_owner=requester,
            institution_name=f"Academy {index}",
            institution_slug=f"academy-{index}",
        )
    client = APIClient()
    client.force_authenticate(user=requester)

    first_page = client.get(REQUESTS_URL)
    second_page = client.get(REQUESTS_URL, {"page": 2})

    assert first_page.status_code == 200
    assert first_page.data["count"] == 21
    assert len(first_page.data["results"]) == 20
    assert first_page.data["next"] is not None
    assert len(second_page.data["results"]) == 1
    assert second_page.data["next"] is None


@pytest.mark.django_db
def test_submission_requires_csrf_for_session_authenticated_user():
    requester = create_user("requester@example.com")
    proposed_owner = create_user("owner@example.com")
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get(reverse("accounts:csrf")).data["csrfToken"]
    login_response = client.post(
        reverse("accounts:login"),
        data=json.dumps({"email": requester.email, "password": "secure-pass"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login_response.status_code == 200
    payload = request_details(proposed_owner)

    csrf_failure = client.post(REQUESTS_URL, payload, format="json")
    valid_token = client.get(reverse("accounts:csrf")).data["csrfToken"]
    success = client.post(
        REQUESTS_URL,
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=valid_token,
    )

    assert csrf_failure.status_code == 403
    assert success.status_code == 201
    assert InstitutionProvisioningRequest.objects.count() == 1
