import pytest
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.institutions.models import Institution, Membership
from apps.institutions.permissions import (
    InstitutionRolePermission,
    InstitutionTenantPermission,
)

User = get_user_model()


class RoleProtectedTestView(APIView):
    permission_classes = [
        IsAuthenticated,
        InstitutionTenantPermission,
        InstitutionRolePermission,
    ]

    def get(self, request, institution_slug):
        return Response({"detail": "allowed"})

    def post(self, request, institution_slug):
        return Response({"detail": "allowed"})


class InstitutionAdminTestView(RoleProtectedTestView):
    allowed_membership_roles = (Membership.Role.INSTITUTION_ADMIN,)


class MissingRoleDeclarationTestView(RoleProtectedTestView):
    pass


class EmptyRoleDeclarationTestView(RoleProtectedTestView):
    allowed_membership_roles = ()


class InvalidRoleDeclarationTestView(RoleProtectedTestView):
    allowed_membership_roles = ("platform_admin",)


@pytest.fixture
def authorization_memberships(db):
    user = User.objects.create_user(email="member@example.com", password="secure-pass")
    non_member = User.objects.create_user(
        email="non-member@example.com",
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
        user=user,
        role=Membership.Role.INSTITUTION_ADMIN,
        status=Membership.Status.ACTIVE,
    )
    membership_b = Membership.objects.create(
        institution=institution_b,
        user=user,
        role=Membership.Role.STUDENT,
        status=Membership.Status.ACTIVE,
    )
    Membership.objects.create(
        institution=institution_a,
        user=non_member,
        role=Membership.Role.STUDENT,
        status=Membership.Status.ACTIVE,
    )
    return {
        "user": user,
        "non_member": non_member,
        "institution_a": institution_a,
        "institution_b": institution_b,
        "membership_a": membership_a,
        "membership_b": membership_b,
    }


def request_view(
    view_class,
    *,
    user,
    slug,
    method="get",
    data=None,
    headers=None,
):
    factory = APIRequestFactory()
    path = f"/test/institutions/{slug}/resource/"
    request_method = getattr(factory, method.lower())
    if method.lower() == "post":
        request = request_method(
            path, data=data or {}, format="json", **(headers or {})
        )
    else:
        request = request_method(path, data=data or {}, **(headers or {}))
    if user is not None:
        force_authenticate(request, user=user)
    return view_class.as_view()(request, institution_slug=slug)


@pytest.mark.django_db
def test_anonymous_user_is_denied(authorization_memberships):
    response = request_view(
        InstitutionAdminTestView,
        user=None,
        slug="north-academy",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_authenticated_non_member_is_denied(authorization_memberships):
    fixture = authorization_memberships

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["non_member"],
        slug=fixture["institution_b"].slug,
    )

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "membership_status",
    [Membership.Status.SUSPENDED, Membership.Status.REMOVED],
)
def test_inactive_membership_is_denied(authorization_memberships, membership_status):
    fixture = authorization_memberships
    fixture["membership_a"].status = membership_status
    fixture["membership_a"].save(update_fields=["status"])

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_a"].slug,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_active_member_with_explicitly_permitted_role_is_allowed(
    authorization_memberships,
):
    fixture = authorization_memberships

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_a"].slug,
    )

    assert response.status_code == 200
    assert response.data == {"detail": "allowed"}


@pytest.mark.django_db
def test_active_member_with_unpermitted_role_is_denied(authorization_memberships):
    fixture = authorization_memberships

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_b"].slug,
    )

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view_class",
    [
        MissingRoleDeclarationTestView,
        EmptyRoleDeclarationTestView,
        InvalidRoleDeclarationTestView,
    ],
)
def test_missing_empty_or_invalid_role_declaration_is_denied(
    authorization_memberships,
    view_class,
):
    fixture = authorization_memberships

    response = request_view(
        view_class,
        user=fixture["user"],
        slug=fixture["institution_a"].slug,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_role_in_another_institution_cannot_authorize_current_tenant(
    authorization_memberships,
):
    fixture = authorization_memberships

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_b"].slug,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_membership_role_change_applies_on_next_request(authorization_memberships):
    fixture = authorization_memberships
    assert (
        request_view(
            InstitutionAdminTestView,
            user=fixture["user"],
            slug=fixture["institution_b"].slug,
        ).status_code
        == 403
    )

    Membership.objects.filter(pk=fixture["membership_b"].pk).update(
        role=Membership.Role.INSTITUTION_ADMIN
    )

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_b"].slug,
    )

    assert response.status_code == 200


def forged_inputs():
    cases = []
    for channel in ("header", "query", "body"):
        for field in ("role", "institution_slug", "institution_id", "membership_id"):
            cases.append((channel, field))
    return cases


@pytest.mark.django_db
@pytest.mark.parametrize(("channel", "field"), forged_inputs())
def test_client_supplied_authorization_values_do_not_grant_access(
    authorization_memberships,
    channel,
    field,
):
    fixture = authorization_memberships
    values = {
        "role": Membership.Role.INSTITUTION_ADMIN,
        "institution_slug": fixture["institution_a"].slug,
        "institution_id": str(fixture["institution_a"].pk),
        "membership_id": str(fixture["membership_a"].pk),
    }
    value = values[field]
    headers = {f"HTTP_X_{field.upper()}": value} if channel == "header" else None
    request_data = {field: value} if channel != "header" else None
    method = "post" if channel == "body" else "get"

    response = request_view(
        InstitutionAdminTestView,
        user=fixture["user"],
        slug=fixture["institution_b"].slug,
        method=method,
        data=request_data,
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_role_permission_requires_resolved_tenant_context(authorization_memberships):
    fixture = authorization_memberships

    class RoleOnlyTestView(APIView):
        permission_classes = [IsAuthenticated, InstitutionRolePermission]
        allowed_membership_roles = (Membership.Role.INSTITUTION_ADMIN,)

        def get(self, request):
            return Response({"detail": "allowed"})

    request = APIRequestFactory().get("/test/no-tenant-context/")
    force_authenticate(request, user=fixture["user"])
    response = RoleOnlyTestView.as_view()(request)

    assert response.status_code == 403
