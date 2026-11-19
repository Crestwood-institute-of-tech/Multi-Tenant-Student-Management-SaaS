from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

from apps.institutions.tenant_context import (
    InstitutionUnavailable,
    MembershipDenied,
    TenantResolver,
)


class InstitutionTenantPermission(BasePermission):
    message = "Access denied."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        institution_slug = getattr(view, "kwargs", {}).get("institution_slug")
        if institution_slug is None:
            raise PermissionDenied("Access denied.")

        try:
            tenant_context = TenantResolver().resolve(
                institution_slug=institution_slug,
                user=request.user,
            )
        except InstitutionUnavailable as exc:
            raise NotFound("Institution unavailable.") from exc
        except MembershipDenied as exc:
            raise PermissionDenied("Access denied.") from exc

        request.tenant_context = tenant_context
        return True
