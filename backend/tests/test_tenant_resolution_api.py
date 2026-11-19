import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from rest_framework.permissions import IsAuthenticated

from apps.institutions.models import Institution, Membership
from apps.institutions.permissions import InstitutionTenantPermission
from apps.institutions.views import InstitutionContextView

User = get_user_model()


def login(client: Client, user: object) -> None:
    response = client.post(
        reverse("accounts:login"),
        data=json.dumps(
            {
                "email": user.email,
                "password": "secure-pass",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert "_auth_user_id" in client.session


def context_url(slug: str) -> str:
    return f"/api/v1/institutions/{slug}/context/"


@pytest.fixture(autouse=True)
def clear_login_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def institution_pair(db):
    user_a = User.objects.create_user(
        email="a@example.com",
        password="secure-pass",
    )
    user_b = User.objects.create_user(
        email="b@example.com",
        password="secure-pass",
    )
    multi = User.objects.create_user(
        email="multi@example.com",
        password="secure-pass",
    )
    institution_a = Institution.objects.create(
        name="North Academy",
        slug="north-academy",
        status=Institution.Status.ACTIVE,
    )
    institution_b = Institution.objects.create(
        name="South Academy",
        slug="south-academy",
        status=Institution.Status.ACTIVE,
    )
    membership_a = Membership.objects.create(
        institution=institution_a,
        user=user_a,
        role=Membership.Role.STUDENT,
        status=Membership.Status.ACTIVE,
    )
    membership_b = Membership.objects.create(
        institution=institution_b,
        user=user_b,
        role=Membership.Role.ACADEMIC_STAFF,
        status=Membership.Status.ACTIVE,
    )
    return {
        "user_a": user_a,
        "user_b": user_b,
        "multi": multi,
        "institution_a": institution_a,
        "institution_b": institution_b,
        "membership_a": membership_a,
        "membership_b": membership_b,
    }


@pytest.mark.django_db
def test_anonymous_request_returns_existing_forbidden_behavior(institution_pair):
    response = Client().get(context_url(institution_pair["institution_a"].slug))

    assert response.status_code == 403


@pytest.mark.django_db
def test_authentication_is_evaluated_before_unknown_tenant_lookup():
    response = Client().get(context_url("unknown-institution"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_valid_session_resolves_minimal_context(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])

    response = client.get(context_url(fixture["institution_a"].slug))

    assert response.status_code == 200
    assert response.json() == {
        "institution": {
            "id": str(fixture["institution_a"].pk),
            "name": "North Academy",
            "slug": "north-academy",
            "status": "active",
        },
        "membership": {
            "id": str(fixture["membership_a"].pk),
            "role": "student",
            "status": "active",
        },
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug", ["unknown-institution", "North-Academy", "north_academy"]
)
def test_unknown_or_malformed_slug_returns_not_found(institution_pair, slug):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])

    response = client.get(context_url(slug))

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("institution_status", ["draft", "active"])
def test_draft_and_active_institutions_resolve(institution_pair, institution_status):
    fixture = institution_pair
    fixture["institution_a"].status = institution_status
    fixture["institution_a"].save(update_fields=["status"])
    client = Client()
    login(client, fixture["user_a"])

    response = client.get(context_url(fixture["institution_a"].slug))

    assert response.status_code == 200
    assert response.json()["institution"]["status"] == institution_status


@pytest.mark.django_db
@pytest.mark.parametrize("institution_status", ["suspended", "closed"])
def test_suspended_or_closed_institution_returns_not_found(
    institution_pair,
    institution_status,
):
    fixture = institution_pair
    fixture["institution_a"].status = institution_status
    fixture["institution_a"].save(update_fields=["status"])
    client = Client()
    login(client, fixture["user_a"])

    response = client.get(context_url(fixture["institution_a"].slug))

    assert response.status_code == 404
    assert "north-academy" not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("membership_case", ["non_member", "suspended", "removed"])
def test_non_member_and_inactive_membership_return_forbidden(
    institution_pair,
    membership_case,
):
    fixture = institution_pair

    if membership_case == "non_member":
        authenticated_user = fixture["user_b"]
        assert not Membership.objects.filter(
            institution=fixture["institution_a"],
            user=authenticated_user,
        ).exists()
    else:
        authenticated_user = fixture["user_a"]
        fixture["membership_a"].status = (
            Membership.Status.SUSPENDED
            if membership_case == "suspended"
            else Membership.Status.REMOVED
        )
        fixture["membership_a"].save(update_fields=["status"])

    client = Client()
    login(client, authenticated_user)

    response = client.get(context_url(fixture["institution_a"].slug))

    assert response.status_code == 403


@pytest.mark.django_db
def test_context_view_permission_classes_are_explicit():
    assert InstitutionContextView.permission_classes == [
        IsAuthenticated,
        InstitutionTenantPermission,
    ]


@pytest.mark.django_db
def test_membership_revocation_takes_effect_on_next_request(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])
    assert client.get(context_url(fixture["institution_a"].slug)).status_code == 200

    fixture["membership_a"].status = Membership.Status.REMOVED
    fixture["membership_a"].save(update_fields=["status"])

    assert client.get(context_url(fixture["institution_a"].slug)).status_code == 403


@pytest.mark.django_db
def test_multi_member_resolves_each_institution_by_its_own_url(institution_pair):
    fixture = institution_pair
    Membership.objects.create(
        institution=fixture["institution_a"],
        user=fixture["multi"],
        role=Membership.Role.STUDENT,
        status=Membership.Status.ACTIVE,
    )
    Membership.objects.create(
        institution=fixture["institution_b"],
        user=fixture["multi"],
        role=Membership.Role.GUARDIAN,
        status=Membership.Status.ACTIVE,
    )
    client = Client()
    login(client, fixture["multi"])

    north = client.get(context_url("north-academy"))
    south = client.get(context_url("south-academy"))

    assert north.status_code == 200
    assert south.status_code == 200
    assert north.json()["membership"]["role"] == "student"
    assert south.json()["membership"]["role"] == "guardian"


@pytest.mark.django_db
def test_user_cannot_guess_another_institution_slug(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])

    own_response = client.get(context_url("north-academy"))
    foreign_response = client.get(context_url("south-academy"))

    assert own_response.status_code == 200
    assert foreign_response.status_code == 403


@pytest.mark.django_db
def test_conflicting_header_and_query_tenant_do_not_override_url(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])

    response = client.get(
        context_url("north-academy"),
        {"institution": "south-academy"},
        HTTP_X_INSTITUTION="south-academy",
    )

    assert response.status_code == 200
    assert response.json()["institution"]["slug"] == "north-academy"


@pytest.mark.django_db
def test_session_selected_tenant_does_not_override_url(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])
    session = client.session
    session["institution_slug"] = "south-academy"
    session.save()

    response = client.get(context_url("north-academy"))

    assert response.status_code == 200
    assert response.json()["institution"]["slug"] == "north-academy"


@pytest.mark.django_db
def test_missing_tenant_context_route_fails_closed(institution_pair):
    fixture = institution_pair
    client = Client()
    login(client, fixture["user_a"])

    response = client.get("/api/v1/institutions//context/")

    assert response.status_code == 404
