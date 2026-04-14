from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AcademicYear(models.Model):
    id = models.BigAutoField(primary_key=True)
    year = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academics_academic_year"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"], name="academics_year_active_idx"),
            models.Index(fields=["is_archived"], name="academics_year_archived_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="academics_single_active_year_constraint",
            )
        ]

    def __str__(self):
        return self.year

    def clean(self):
        if self.is_archived and self.is_active:
            raise ValidationError({"is_active": "Archived academic year cannot be active."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
