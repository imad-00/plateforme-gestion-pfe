import uuid

from django.db import models


class DeliverableSubmission(models.Model):
    class DeliverableType(models.TextChoices):
        REPORT = "REPORT", "Report"
        CAHIER_DES_CHARGES = "CAHIER_DES_CHARGES", "Cahier des charges"
        OTHER = "OTHER", "Other"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        NEEDS_REVISION = "NEEDS_REVISION", "Needs revision"
        REJECTED = "REJECTED", "Rejected"

    submission_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="deliverable_submissions",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="deliverable_submissions",
    )
    type = models.CharField(max_length=24, choices=DeliverableType.choices)
    version_number = models.PositiveIntegerField(default=1)
    file_url = models.CharField(max_length=500)
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    review_status = models.CharField(
        max_length=16,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="reviewed_deliverables",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "deliverables_submission"
        indexes = [
            models.Index(fields=["team"], name="deliverables_team_idx"),
            models.Index(fields=["type"], name="deliverables_type_idx"),
            models.Index(fields=["review_status"], name="deliverables_review_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "type", "version_number"],
                name="deliverables_unique_version_per_team_type",
            )
        ]
