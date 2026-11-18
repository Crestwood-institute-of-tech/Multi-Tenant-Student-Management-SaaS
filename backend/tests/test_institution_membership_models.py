import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.institutions.models import Institution, Membership

User = get_user_model()


def create_user(email: str = "member@example.com") -> object:
    return User.objects.create_user(email=email, password="secure-pass")


@pytest.mark.django_db
def test_institution_uuid_primary_key_and_default_status():
    institution = Institution.objects.create(name="North Academy", slug="north-academy")

    assert isinstance(institution.pk, uuid.UUID)
    assert institution.status == Institution.Status.DRAFT
    assert list(Institution.Status.values) == [
        "draft",
        "active",
        "suspended",
        "closed",
    ]


@pytest.mark.django_db
def test_institution_requires_name():
    institution = Institution(name="", slug="north-academy")

    with pytest.raises(ValidationError):
        institution.full_clean()


@pytest.mark.django_db
def test_institution_slug_is_normalized_and_lowercased():
    institution = Institution(name="North Academy", slug="  North-Academy  ")

    institution.full_clean()

    assert institution.slug == "north-academy"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug", ["", "North Academy", "north_academy", "-north", "north-"]
)
def test_institution_rejects_invalid_slugs(slug):
    institution = Institution(name="North Academy", slug=slug)

    with pytest.raises(ValidationError):
        institution.full_clean()


@pytest.mark.django_db
def test_institution_duplicate_slug_rejection():
    Institution.objects.create(name="North Academy", slug="north-academy")

    with pytest.raises(ValidationError):
        Institution.objects.create(name="Other Academy", slug="NORTH-ACADEMY")


@pytest.mark.django_db
def test_institution_slug_is_immutable():
    institution = Institution.objects.create(name="North Academy", slug="north-academy")
    institution.slug = "new-slug"

    with pytest.raises(ValidationError) as exc_info:
        institution.save()

    assert "slug" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["", "   ", "\t\r\n"])
def test_institution_database_rejects_blank_names(name):
    with pytest.raises(IntegrityError), transaction.atomic():
        Institution.objects.bulk_create(
            [Institution(name=name, slug="database-name-test")]
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug",
    [
        "Upper-Slug",
        "north_academy",
        "-north-academy",
        "north-academy-",
        "north--academy",
    ],
)
def test_institution_database_rejects_noncanonical_slugs(slug):
    with pytest.raises(IntegrityError), transaction.atomic():
        Institution.objects.bulk_create(
            [Institution(name="Database Slug Test", slug=slug)]
        )


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["a", "123", "abc-123"])
def test_institution_database_accepts_canonical_slugs(slug):
    Institution.objects.bulk_create(
        [Institution(name="Database Canonical Slug", slug=slug)]
    )

    assert Institution.objects.filter(slug=slug).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["", "north academy", "north\n"])
def test_institution_database_rejects_empty_spaced_or_newline_slugs(slug):
    with pytest.raises(IntegrityError), transaction.atomic():
        Institution.objects.bulk_create(
            [Institution(name="Database Slug Test", slug=slug)]
        )


@pytest.mark.django_db
def test_institution_invalid_status_rejected_by_database_constraint():
    with pytest.raises(IntegrityError), transaction.atomic():
        Institution.objects.bulk_create(
            [Institution(name="Invalid", slug="invalid", status="invalid")]
        )


@pytest.mark.django_db
def test_membership_uuid_primary_key_and_default_status():
    user = create_user()
    institution = Institution.objects.create(name="North Academy", slug="north-academy")
    membership = Membership.objects.create(
        institution=institution,
        user=user,
        role=Membership.Role.STUDENT,
    )

    assert isinstance(membership.pk, uuid.UUID)
    assert membership.status == Membership.Status.ACTIVE
    assert set(Membership.Role.values) == {
        "institution_admin",
        "academic_staff",
        "finance_staff",
        "student",
        "guardian",
    }
    assert set(Membership.Status.values) == {"active", "suspended", "removed"}


@pytest.mark.django_db
def test_same_user_can_belong_to_two_institutions():
    user = create_user()
    north = Institution.objects.create(name="North", slug="north")
    south = Institution.objects.create(name="South", slug="south")

    Membership.objects.create(
        institution=north, user=user, role=Membership.Role.STUDENT
    )
    Membership.objects.create(
        institution=south, user=user, role=Membership.Role.GUARDIAN
    )

    assert Membership.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_duplicate_institution_user_membership_rejected():
    user = create_user()
    institution = Institution.objects.create(name="North", slug="north")
    Membership.objects.create(
        institution=institution,
        user=user,
        role=Membership.Role.STUDENT,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(
            institution=institution,
            user=user,
            role=Membership.Role.GUARDIAN,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("role", "invalid"), ("status", "invalid")],
)
def test_membership_invalid_values_rejected_by_database_constraint(
    field, invalid_value
):
    user = create_user()
    institution = Institution.objects.create(name="North", slug="north")
    values = {
        "institution": institution,
        "user": user,
        "role": Membership.Role.STUDENT,
        "status": Membership.Status.ACTIVE,
    }
    values[field] = invalid_value

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create([Membership(**values)])


@pytest.mark.django_db
def test_deleting_referenced_institution_is_protected():
    user = create_user()
    institution = Institution.objects.create(name="North", slug="north")
    Membership.objects.create(
        institution=institution,
        user=user,
        role=Membership.Role.STUDENT,
    )

    with pytest.raises(ProtectedError):
        institution.delete()

    assert Institution.objects.filter(pk=institution.pk).exists()


@pytest.mark.django_db
def test_deleting_referenced_user_is_protected():
    user = create_user()
    institution = Institution.objects.create(name="North", slug="north")
    Membership.objects.create(
        institution=institution,
        user=user,
        role=Membership.Role.STUDENT,
    )

    with pytest.raises(ProtectedError):
        user.delete()

    assert User.objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_removed_membership_retains_row_and_enforces_uniqueness():
    user = create_user()
    institution = Institution.objects.create(name="North", slug="north")
    membership = Membership.objects.create(
        institution=institution,
        user=user,
        role=Membership.Role.STUDENT,
    )
    membership.status = Membership.Status.REMOVED
    membership.save()

    assert Membership.objects.filter(pk=membership.pk).exists()

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create(
            [
                Membership(
                    institution=institution,
                    user=user,
                    role=Membership.Role.GUARDIAN,
                    status=Membership.Status.ACTIVE,
                )
            ]
        )
