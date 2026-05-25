import uuid
from pathlib import Path

from django.db import models
from django.utils.text import get_valid_filename


def deliverable_upload_to(instance, filename):
    safe_name = get_valid_filename(Path(filename).name or "deliverable")
    return f"deliverables/{instance.team.academic_year_id}/{instance.team_id}/{safe_name}"


class DeliverableFile(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        NEEDS_REVISION = "NEEDS_REVISION", "Needs Revision"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.PROTECT,
        related_name="deliverable_files",
    )
    file = models.FileField(upload_to=deliverable_upload_to)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="uploaded_deliverable_files",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="reviewed_deliverable_files",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deliverables_file"
        ordering = ["-uploaded_at", "-created_at"]
        indexes = [
            models.Index(fields=["team"], name="deliverables_file_team_idx"),
            models.Index(fields=["uploaded_by"], name="deliverables_file_uploader_idx"),
            models.Index(fields=["review_status"], name="deliverables_file_review_idx"),
            models.Index(fields=["uploaded_at"], name="deliverables_file_uploaded_idx"),
        ]

    def __str__(self):
        return f"{self.team_id} - {self.original_filename} ({self.review_status})"


class DeliverableFileComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deliverable_file = models.ForeignKey(
        "deliverables.DeliverableFile",
        on_delete=models.PROTECT,
        related_name="comments",
    )
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="deliverable_file_comments",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deliverables_file_comment"
        ordering = ["created_at", "updated_at"]
        indexes = [
            models.Index(fields=["deliverable_file"], name="deliverables_comment_file_idx"),
            models.Index(fields=["author"], name="deliv_comment_author_idx"),
            models.Index(fields=["created_at"], name="deliv_comment_created_idx"),
        ]

    def __str__(self):
        return f"{self.deliverable_file_id} - {self.author_id}"
