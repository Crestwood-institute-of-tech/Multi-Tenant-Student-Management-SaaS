import re
from dataclasses import dataclass

from apps.institutions.models import Institution, Membership

CANONICAL_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class TenantContext:
    institution: Institution
    membership: Membership


class InstitutionUnavailable(Exception):
    pass


class MembershipDenied(Exception):
    pass


class TenantResolver:
    def resolve(self, *, institution_slug: object, user: object) -> TenantContext:
        if not isinstance(institution_slug, str):
            raise InstitutionUnavailable
        if not CANONICAL_SLUG_PATTERN.fullmatch(institution_slug):
            raise InstitutionUnavailable

        institution = Institution.objects.filter(slug=institution_slug).first()
        if institution is None:
            raise InstitutionUnavailable
        if institution.status not in (
            Institution.Status.DRAFT,
            Institution.Status.ACTIVE,
        ):
            raise InstitutionUnavailable

        membership = Membership.objects.filter(
            institution=institution,
            user=user,
        ).first()
        if membership is None:
            raise MembershipDenied
        if membership.status != Membership.Status.ACTIVE:
            raise MembershipDenied

        return TenantContext(institution=institution, membership=membership)
