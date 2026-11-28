from django.urls import path

from apps.institutions.provisioning_views import (
    InstitutionProvisioningRequestDetailView,
    InstitutionProvisioningRequestListCreateView,
)

app_name = "institution_provisioning"

urlpatterns = [
    path(
        "requests/",
        InstitutionProvisioningRequestListCreateView.as_view(),
        name="request-list",
    ),
    path(
        "requests/<uuid:request_id>/",
        InstitutionProvisioningRequestDetailView.as_view(),
        name="request-detail",
    ),
]
