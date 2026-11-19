import logging

from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

from apps.institutions.models import Institution, Membership
from apps.institutions.tenant_context import (
    InstitutionUnavailable,
    MembershipDenied,
    TenantContext,
    TenantResolver,
)

logger = logging.getLogger(__name__)


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


class InstitutionRolePermission(BasePermission):
    message = "Access denied."
    role_declaration_attribute = "allowed_membership_roles"
    valid_roles = frozenset(Membership.Role.values)

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        tenant_context = getattr(request, "tenant_context", None)
        if not isinstance(tenant_context, TenantContext):
            return False
        if not isinstance(tenant_context.institution, Institution):
            return False
        if not isinstance(tenant_context.membership, Membership):
            return False
        if (
            tenant_context.membership.institution_id != tenant_context.institution.pk
            or tenant_context.membership.user_id != request.user.pk
        ):
            return False

        declaration = vars(type(view)).get(self.role_declaration_attribute)
        if (
            not isinstance(declaration, (tuple, frozenset))
            or not declaration
            or any(
                not isinstance(role, str) or role not in self.valid_roles
                for role in declaration
            )
        ):
            logger.error(
                "View %s has a missing or invalid membership role declaration.",
                type(view).__name__,
            )
            return False

        current_role = (
            Membership.objects.filter(
                institution=tenant_context.institution,
                user=request.user,
                status=Membership.Status.ACTIVE,
            )
            .values_list("role", flat=True)
            .first()
        )
        return current_role in declaration
