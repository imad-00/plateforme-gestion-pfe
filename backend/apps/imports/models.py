from django.db import models
from django.utils import timezone


class UserImportBatch(models.Model):
    class ImportType(models.TextChoices):
        STUDENTS = "STUDENTS", "Students"
        TEACHERS = "TEACHERS", "Teachers"

    class Status(models.TextChoices):
        PREVIEWED = "PREVIEWED", "Previewed"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        EXPIRED = "EXPIRED", "Expired"

    id = models.BigAutoField(primary_key=True)
    import_type = models.CharField(max_length=16, choices=ImportType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEWED)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="user_import_batches",
    )
    original_filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    normalized_rows = models.JSONField(default=list, blank=True)
    created_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "imports_user_import_batch"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["import_type"], name="imports_batch_type_idx"),
            models.Index(fields=["status"], name="imports_batch_status_idx"),
            models.Index(fields=["uploaded_by"], name="imports_batch_uploader_idx"),
        ]

    def __str__(self):
        return f"{self.import_type} import #{self.id} ({self.status})"
