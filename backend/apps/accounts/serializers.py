from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        allow_blank=False,
        max_length=1024,
        trim_whitespace=False,
        write_only=True,
    )


class AuthenticatedUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)


class LoginResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()


class CsrfTokenSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()
