from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.institutions.permissions import InstitutionTenantPermission


class InstitutionContextView(APIView):
    permission_classes = [IsAuthenticated, InstitutionTenantPermission]

    @extend_schema(
        tags=["institutions"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "institution": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                            "slug": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                    "membership": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "role": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                },
            }
        },
    )
    def get(self, request, institution_slug):
        tenant_context = request.tenant_context
        institution = tenant_context.institution
        membership = tenant_context.membership
        return Response(
            {
                "institution": {
                    "id": str(institution.pk),
                    "name": institution.name,
                    "slug": institution.slug,
                    "status": institution.status,
                },
                "membership": {
                    "id": str(membership.pk),
                    "role": membership.role,
                    "status": membership.status,
                },
            }
        )
