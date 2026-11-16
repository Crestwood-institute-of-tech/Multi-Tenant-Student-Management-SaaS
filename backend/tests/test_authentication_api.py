import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

User = get_user_model()
CSRF_URL = reverse("accounts:csrf")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
CURRENT_USER_URL = reverse("accounts:me")


def get_csrf_token(client):
    response = client.get(CSRF_URL)
    assert response.status_code == 200
    return response.json()["csrfToken"]


@pytest.fixture(autouse=True)
def clear_login_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def post_login(client, email, password, csrf_token=None):
    headers = {}
    if csrf_token is not None:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token
    return client.post(
        LOGIN_URL,
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
def test_login_creates_session_and_rotates_anonymous_session_identifier():
    user = User.objects.create_user(
        email="student@example.com",
        password="secure-pass",
    )
    client = Client(enforce_csrf_checks=True)
    anonymous_session = client.session
    anonymous_session["pre_login"] = "value"
    anonymous_session.save()
    old_session_key = anonymous_session.session_key
    csrf_token = get_csrf_token(client)
    old_csrf_cookie = client.cookies["csrftoken"].value

    response = post_login(client, "student@example.com", "secure-pass", csrf_token)

    assert response.status_code == 200
    assert response.json() == {
        "user": {"id": str(user.pk), "email": "student@example.com"}
    }
    assert client.session.session_key != old_session_key
    assert client.session["_auth_user_id"] == str(user.pk)
    assert "auth_session_started_at" in client.session
    assert "sessionid" in response.cookies
    assert response.cookies["csrftoken"].value != old_csrf_cookie
    assert "secure-pass" not in response.content.decode()
    assert response.cookies["sessionid"].value not in response.content.decode()


@pytest.mark.django_db
def test_login_normalizes_email_using_the_user_manager():
    User.objects.create_user(email="Student@Example.COM", password="secure-pass")
    client = Client(enforce_csrf_checks=True)

    response = post_login(
        client,
        " Student@example.com ",
        "secure-pass",
        get_csrf_token(client),
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "Student@example.com"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("student@example.com", "wrong-password"),
        ("unknown@example.com", "wrong-password"),
    ],
)
def test_login_returns_same_generic_failure_for_invalid_credentials(email, password):
    User.objects.create_user(email="student@example.com", password="secure-pass")
    client = Client(enforce_csrf_checks=True)

    response = post_login(client, email, password, get_csrf_token(client))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_inactive_user_cannot_create_a_session():
    User.objects.create_user(
        email="inactive@example.com",
        password="secure-pass",
        is_active=False,
    )
    client = Client(enforce_csrf_checks=True)

    response = post_login(
        client,
        "inactive@example.com",
        "secure-pass",
        get_csrf_token(client),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_deactivated_user_cannot_reuse_an_existing_session():
    user = User.objects.create_user(
        email="student@example.com",
        password="secure-pass",
    )
    client = Client()
    assert post_login(client, user.email, "secure-pass").status_code == 200
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.get(CURRENT_USER_URL)

    assert response.status_code == 403


@pytest.mark.django_db
def test_login_rejects_missing_or_invalid_csrf_token():
    User.objects.create_user(email="student@example.com", password="secure-pass")
    client = Client(enforce_csrf_checks=True)
    get_csrf_token(client)

    missing_token = post_login(client, "student@example.com", "secure-pass")
    invalid_token = post_login(
        client,
        "student@example.com",
        "secure-pass",
        "invalid-token",
    )

    assert missing_token.status_code == 403
    assert missing_token.json() == {"detail": "CSRF verification failed."}
    assert invalid_token.status_code == 403
    assert invalid_token.json() == {"detail": "CSRF verification failed."}


@pytest.mark.django_db
def test_logout_invalidates_session_and_requires_csrf():
    User.objects.create_user(email="student@example.com", password="secure-pass")
    client = Client(enforce_csrf_checks=True)
    login_response = post_login(
        client,
        "student@example.com",
        "secure-pass",
        get_csrf_token(client),
    )
    assert login_response.status_code == 200

    no_csrf = client.post(LOGOUT_URL, data="{}", content_type="application/json")
    csrf_token = get_csrf_token(client)
    invalid_csrf = client.post(
        LOGOUT_URL,
        data="{}",
        content_type="application/json",
        HTTP_X_CSRFTOKEN="invalid-token",
    )
    logout_response = client.post(
        LOGOUT_URL,
        data="{}",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert no_csrf.status_code == 403
    assert invalid_csrf.status_code == 403
    assert logout_response.status_code == 200
    assert logout_response.json() == {"detail": "Logged out."}
    assert client.get(CURRENT_USER_URL).status_code == 403


@pytest.mark.django_db
def test_unauthenticated_logout_is_denied_even_with_csrf():
    client = Client(enforce_csrf_checks=True)
    csrf_token = get_csrf_token(client)

    response = client.post(
        LOGOUT_URL,
        data="{}",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_current_user_returns_only_safe_profile_fields():
    user = User.objects.create_user(
        email="student@example.com",
        password="secure-pass",
        first_name="Student",
        last_name="Example",
        is_staff=True,
        is_superuser=True,
    )
    client = Client()
    assert post_login(client, user.email, "secure-pass").status_code == 200

    response = client.get(CURRENT_USER_URL)

    assert response.status_code == 200
    assert response.json() == {"id": str(user.pk), "email": user.email}
    body = response.content.decode()
    assert user.password not in body
    assert "secure-pass" not in body
    assert "is_staff" not in body
    assert "is_superuser" not in body
    assert client.cookies["sessionid"].value not in body


def test_current_user_requires_authentication():
    response = Client().get(CURRENT_USER_URL)

    assert response.status_code == 403


def test_csrf_endpoint_returns_token_and_http_only_cookie():
    response = Client(enforce_csrf_checks=True).get(CSRF_URL)

    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    assert response.json()["csrfToken"]
    csrf_cookie = response.cookies["csrftoken"]
    assert csrf_cookie["httponly"] is True
    assert csrf_cookie["samesite"] == "Lax"
    assert csrf_cookie["path"] == "/"


def test_cors_credentials_are_limited_to_configured_origin():
    allowed_client = Client()
    disallowed_client = Client()
    with override_settings(
        CORS_ALLOWED_ORIGINS=["https://frontend.example.test"],
        CORS_ALLOW_CREDENTIALS=True,
    ):
        allowed = allowed_client.get(
            CSRF_URL,
            HTTP_ORIGIN="https://frontend.example.test",
        )
        disallowed = disallowed_client.get(
            CSRF_URL,
            HTTP_ORIGIN="https://untrusted.example.test",
        )

    assert allowed["Access-Control-Allow-Origin"] == "https://frontend.example.test"
    assert allowed["Access-Control-Allow-Credentials"] == "true"
    assert "Access-Control-Allow-Origin" not in disallowed


@pytest.mark.django_db
@override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_session_and_csrf_cookies_apply_secure_attributes_when_enabled():
    User.objects.create_user(email="student@example.com", password="secure-pass")
    client = Client(enforce_csrf_checks=True)
    csrf_response = client.get(CSRF_URL)

    assert csrf_response.cookies["csrftoken"]["secure"] is True

    response = post_login(
        client,
        "student@example.com",
        "secure-pass",
        csrf_response.json()["csrfToken"],
    )

    assert response.status_code == 200
    session_cookie = response.cookies["sessionid"]
    assert session_cookie["secure"] is True
    assert session_cookie["httponly"] is True
    assert session_cookie["samesite"] == "Lax"
    assert session_cookie["path"] == "/"
    assert session_cookie["max-age"] == settings.SESSION_COOKIE_AGE


@pytest.mark.django_db
def test_authenticated_session_expires_at_absolute_lifetime():
    User.objects.create_user(email="student@example.com", password="secure-pass")
    client = Client()
    assert post_login(client, "student@example.com", "secure-pass").status_code == 200
    session = client.session
    session["auth_session_started_at"] = (
        timezone.now().timestamp() - settings.AUTH_SESSION_ABSOLUTE_AGE - 1
    )
    session.save()

    response = client.get(CURRENT_USER_URL)

    assert response.status_code == 403
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_authentication_state_is_isolated_between_clients():
    User.objects.create_user(email="student@example.com", password="secure-pass")
    authenticated_client = Client()
    unauthenticated_client = Client()
    assert (
        post_login(
            authenticated_client,
            "student@example.com",
            "secure-pass",
        ).status_code
        == 200
    )

    assert authenticated_client.get(CURRENT_USER_URL).status_code == 200
    assert unauthenticated_client.get(CURRENT_USER_URL).status_code == 403


@pytest.mark.django_db
def test_login_throttle_returns_too_many_requests():
    client = Client(enforce_csrf_checks=True)
    csrf_token = get_csrf_token(client)

    responses = [
        post_login(client, "unknown@example.com", "wrong-password", csrf_token)
        for _ in range(11)
    ]

    assert all(response.status_code == 401 for response in responses[:10])
    assert responses[10].status_code == 429
