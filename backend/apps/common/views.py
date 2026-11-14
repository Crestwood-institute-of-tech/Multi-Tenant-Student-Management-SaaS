import logging

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import HealthResponseSerializer

logger = logging.getLogger(__name__)
SERVICE_NAME = "student-management-api"


class LivenessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["health"],
        responses=HealthResponseSerializer,
        description=(
            "Confirms that the API process is responsive without querying dependencies."
        ),
    )
    def get(self, request):
        return Response({"status": "ok", "service": SERVICE_NAME})


class ReadinessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["health"],
        responses={200: HealthResponseSerializer, 503: HealthResponseSerializer},
        description="Confirms that the API can reach its configured database.",
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.exception("Database readiness check failed.")
            return Response(
                {"status": "unavailable", "service": SERVICE_NAME},
                status=503,
            )

        return Response({"status": "ok", "service": SERVICE_NAME})
