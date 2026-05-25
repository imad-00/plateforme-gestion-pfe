from django.conf import settings
from django.db import models
from django.utils import timezone


class AcademicYearLifecycleEvent(models.Model):
    class EventType(models.TextChoices):
        CLOSED = "CLOSED", "Closed"
        FORCE_CLOSED = "FORCE_CLOSED", "Force Closed"
        REOPENED = "REOPENED", "Reopened"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.BigAutoField(primary_key=True)
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="lifecycle_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_year_lifecycle_events",
    )
    performed_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "archives_academic_year_lifecycle_event"
        ordering = ["-performed_at", "-created_at"]
        indexes = [
            models.Index(fields=["academic_year"], name="archive_life_year_idx"),
            models.Index(fields=["event_type"], name="archive_life_event_idx"),
            models.Index(fields=["performed_at"], name="archive_life_time_idx"),
        ]

    def __str__(self):
        return f"{self.academic_year_id} - {self.event_type} @ {self.performed_at.isoformat()}"
