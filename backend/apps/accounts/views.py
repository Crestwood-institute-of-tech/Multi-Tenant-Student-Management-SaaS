from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.middleware import AUTH_SESSION_STARTED_AT
from apps.accounts.serializers import (
    AuthenticatedUserSerializer,
    CsrfTokenSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    MessageSerializer,
)

User = get_user_model()
INVALID_CREDENTIALS = {"detail": "Invalid email or password."}


def csrf_failure(request, reason=""):
    return JsonResponse({"detail": "CSRF verification failed."}, status=403)


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["authentication"],
        responses=CsrfTokenSerializer,
        description="Returns a CSRF token for subsequent unsafe browser requests.",
    )
    def get(self, request):
        return Response(
            {"csrfToken": get_token(request)},
            headers={"Cache-Control": "no-store"},
        )


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    @extend_schema(
        tags=["authentication"],
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: MessageSerializer,
            401: MessageSerializer,
            429: MessageSerializer,
        },
        description="Authenticates an account and establishes a server-side session.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = User.objects.normalize_email(serializer.validated_data["email"].strip())
        user = authenticate(
            request,
            email=email,
            password=serializer.validated_data["password"],
        )

        if user is None or not user.is_active:
            return Response(INVALID_CREDENTIALS, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        request.session[AUTH_SESSION_STARTED_AT] = timezone.now().timestamp()
        return Response(
            {"user": AuthenticatedUserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


@method_decorator(never_cache, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["authentication"],
        request=None,
        responses=MessageSerializer,
        description="Invalidates the current authenticated session.",
    )
    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


@method_decorator(never_cache, name="dispatch")
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["authentication"],
        responses=AuthenticatedUserSerializer,
        description="Returns the minimal profile for the authenticated account.",
    )
    def get(self, request):
        return Response(AuthenticatedUserSerializer(request.user).data)
