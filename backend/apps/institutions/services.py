import uuid

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.institutions.models import InstitutionProvisioningRequest

User = get_user_model()


@transaction.atomic
def create_institution_provisioning_request(
    *,
    requesting_user: User,
    proposed_owner: User,
    institution_name: str,
    institution_slug: str,
) -> InstitutionProvisioningRequest:
    request = InstitutionProvisioningRequest(
        requesting_user=requesting_user,
        proposed_owner=proposed_owner,
        institution_name=institution_name,
        institution_slug=institution_slug,
    )
    request.full_clean()
    request.save()
    return request


def get_institution_provisioning_request(
    request_id: uuid.UUID,
) -> InstitutionProvisioningRequest:
    return InstitutionProvisioningRequest.objects.get(pk=request_id)
