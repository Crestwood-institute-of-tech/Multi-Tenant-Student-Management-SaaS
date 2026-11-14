import uuid

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_uses_email_for_authentication_and_uuid_primary_key():
    user = User.objects.create_user(email="Student@Example.COM", password="secure-pass")

    assert user.email == "Student@example.com"
    assert isinstance(user.pk, uuid.UUID)
    assert User.USERNAME_FIELD == "email"
    assert user.check_password("secure-pass")


@pytest.mark.django_db
def test_create_user_rejects_missing_email():
    with pytest.raises(ValueError, match="email address is required"):
        User.objects.create_user(email="", password="secure-pass")


@pytest.mark.django_db
def test_create_superuser_sets_required_privileges():
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="secure-pass",
    )

    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [("is_staff", False), ("is_superuser", False)],
)
def test_create_superuser_rejects_missing_privileges(field, value):
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.com",
            password="secure-pass",
            **{field: value},
        )
