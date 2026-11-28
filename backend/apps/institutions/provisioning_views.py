from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.institutions.models import InstitutionProvisioningRequest
from apps.institutions.provisioning_serializers import (
    InstitutionProvisioningRequestCreateSerializer,
    InstitutionProvisioningRequestSerializer,
)


class InstitutionProvisioningRequestPagination(PageNumberPagination):
    page_size = 20


class InstitutionProvisioningRequestListCreateView(generics.ListAPIView):
    serializer_class = InstitutionProvisioningRequestSerializer
    pagination_class = InstitutionProvisioningRequestPagination
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "institution_provisioning"

    def get_queryset(self):
        return InstitutionProvisioningRequest.objects.filter(
            requesting_user=self.request.user
        ).order_by("-created_at", "-pk")

    @extend_schema(
        tags=["institution-provisioning"],
        responses=InstitutionProvisioningRequestSerializer(many=True),
        description=(
            "Returns only the session user's requests, paginated at 20 items per page."
        ),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["institution-provisioning"],
        request=InstitutionProvisioningRequestCreateSerializer,
        responses={201: InstitutionProvisioningRequestSerializer},
        description=(
            "Submits a provisioning request. The requester is derived from the "
            "authenticated session; this endpoint does not create an institution "
            "or membership."
        ),
    )
    def post(self, request, *args, **kwargs):
        input_serializer = InstitutionProvisioningRequestCreateSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        input_serializer.is_valid(raise_exception=True)
        provisioning_request = input_serializer.save(
            requesting_user=request.user,
        )
        return Response(
            InstitutionProvisioningRequestSerializer(provisioning_request).data,
            status=status.HTTP_201_CREATED,
        )


class InstitutionProvisioningRequestDetailView(generics.RetrieveAPIView):
    serializer_class = InstitutionProvisioningRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "institution_provisioning"
    lookup_url_kwarg = "request_id"

    def get_queryset(self):
        return InstitutionProvisioningRequest.objects.filter(
            requesting_user=self.request.user
        )

    @extend_schema(
        tags=["institution-provisioning"],
        responses={200: InstitutionProvisioningRequestSerializer},
        description=(
            "Retrieves a request only when it was submitted by the authenticated "
            "session user."
        ),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
