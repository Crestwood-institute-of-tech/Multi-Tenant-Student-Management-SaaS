from django.urls import path

from apps.common.views import LivenessView, ReadinessView

app_name = "common"

urlpatterns = [
    path("health/", LivenessView.as_view(), name="health"),
    path("health/ready/", ReadinessView.as_view(), name="readiness"),
]
