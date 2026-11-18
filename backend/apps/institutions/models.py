import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

canonical_slug_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message="Enter a valid canonical slug.",
)


class Institution(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.CharField(
        max_length=63,
        unique=True,
        validators=[canonical_slug_validator],
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"),
                name="institution_name_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(slug__regex=r"^[a-z0-9]+(-[a-z0-9]+)*\Z"),
                name="institution_slug_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("draft", "active", "suspended", "closed")
                ),
                name="institution_status_valid",
            ),
        ]

    def clean_fields(self, exclude=None) -> None:
        if self.slug is not None:
            self.slug = self.slug.strip().lower()
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        if self.slug is not None:
            self.slug = self.slug.strip().lower()

        if not self._state.adding:
            existing_slug = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if existing_slug is not None and self.slug != existing_slug:
                raise ValidationError({"slug": "The institution slug is immutable."})

    def save(self, *args, **kwargs) -> None:
        if self.slug is not None:
            self.slug = self.slug.strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        INSTITUTION_ADMIN = "institution_admin", "Institution admin"
        ACADEMIC_STAFF = "academic_staff", "Academic staff"
        FINANCE_STAFF = "finance_staff", "Finance staff"
        STUDENT = "student", "Student"
        GUARDIAN = "guardian", "Guardian"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="institution_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("institution", "user"),
                name="unique_institution_user_membership",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=(
                        "institution_admin",
                        "academic_staff",
                        "finance_staff",
                        "student",
                        "guardian",
                    )
                ),
                name="membership_role_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("active", "suspended", "removed")),
                name="membership_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.institution_id}: {self.role}"
