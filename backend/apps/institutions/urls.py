from django.urls import path

from apps.institutions.views import InstitutionContextView

app_name = "institutions"

urlpatterns = [
    path(
        "<str:institution_slug>/context/",
        InstitutionContextView.as_view(),
        name="institution-context",
    ),
]
