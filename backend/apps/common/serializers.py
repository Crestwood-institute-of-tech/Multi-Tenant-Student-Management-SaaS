from rest_framework import serializers


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("ok", "unavailable"))
    service = serializers.CharField()
