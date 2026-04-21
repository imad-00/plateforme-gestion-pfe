from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AcademicYear(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.BigAutoField(primary_key=True)
    year = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CLOSED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academics_academic_year"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="academics_year_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["status"],
                condition=Q(status="ACTIVE"),
                name="academics_single_active_year_constraint",
            )
        ]

    def __str__(self):
        return self.year

    def clean(self):
        if self.status not in self.Status.values:
            raise ValidationError({"status": "Invalid academic year status."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
