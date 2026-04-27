from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class AcademicYear(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.BigAutoField(primary_key=True)
    year = models.CharField(max_length=20, unique=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CLOSED,
    )
    wishlist_size = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Number of subject choices required in each team wishlist.",
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

    @property
    def year_label(self):
        return self.year

    def clean(self):
        if self.status not in self.Status.values:
            raise ValidationError({"status": "Invalid academic year status."})
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "end_date must be greater than or equal to start_date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
