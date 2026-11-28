from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.institutions.models import InstitutionProvisioningRequest
from apps.institutions.services import create_institution_provisioning_request

User = get_user_model()


class InstitutionProvisioningRequestSerializer(serializers.ModelSerializer):
    proposed_owner = serializers.UUIDField(
        source="proposed_owner_id",
        read_only=True,
    )

    class Meta:
        model = InstitutionProvisioningRequest
        fields = (
            "id",
            "institution_name",
            "institution_slug",
            "proposed_owner",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InstitutionProvisioningRequestCreateSerializer(serializers.Serializer):
    institution_name = serializers.CharField(max_length=255, allow_blank=False)
    institution_slug = serializers.CharField(max_length=63, allow_blank=False)
    proposed_owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError(
                    {field: ["Unknown field."] for field in sorted(unknown_fields)}
                )
        return super().to_internal_value(data)

    def create(self, validated_data):
        requesting_user = validated_data.pop("requesting_user")
        try:
            return create_institution_provisioning_request(
                requesting_user=requesting_user,
                **validated_data,
            )
        except DjangoValidationError as exc:
            errors = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            raise serializers.ValidationError(errors) from exc
