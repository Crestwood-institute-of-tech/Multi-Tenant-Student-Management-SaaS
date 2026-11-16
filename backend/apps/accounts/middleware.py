import math

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

AUTH_SESSION_STARTED_AT = "auth_session_started_at"


class AuthenticationSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            started_at = request.session.get(AUTH_SESSION_STARTED_AT)
            now = timezone.now().timestamp()
            max_age = settings.AUTH_SESSION_ABSOLUTE_AGE

            if (
                type(started_at) not in (int, float)
                or not math.isfinite(started_at)
                or started_at > now
                or now - started_at >= max_age
            ):
                request.session.flush()
                request.user = AnonymousUser()

        return self.get_response(request)
