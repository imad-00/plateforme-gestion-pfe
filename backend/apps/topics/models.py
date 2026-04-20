from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Subject(models.Model):
    class SubjectType(models.TextChoices):
        RESEARCH_PROJECT = "RESEARCH_PROJECT", "Research Project"
        APPLIED_PROJECT = "APPLIED_PROJECT", "Applied Project"
        STARTUP_PROJECT = "STARTUP_PROJECT", "Startup Project"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ASSIGNED = "ASSIGNED", "Assigned"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    subject_type = models.CharField(max_length=32, choices=SubjectType.choices)
    technologies = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    attachment_key = models.CharField(max_length=255, blank=True)
    attachment_original_name = models.CharField(max_length=255, blank=True)
    attachment_mime_type = models.CharField(max_length=100, blank=True)
    attachment_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proposed_subjects",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="subjects",
    )

    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_subjects",
        null=True,
        blank=True,
    )

    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "topics_subject"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="topics_subject_status_idx"),
            models.Index(fields=["is_archived"], name="topics_subject_archived_idx"),
            models.Index(fields=["academic_year"], name="topics_subject_year_idx"),
            models.Index(fields=["proposed_by"], name="topics_subject_teacher_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_editable_by_teacher(self):
        return not self.is_archived and self.status in {self.Status.DRAFT, self.Status.REJECTED}

    def clean(self):
        if self.academic_year_id and self.academic_year.is_archived:
            raise ValidationError({"academic_year": "Subject cannot be linked to an archived academic year."})

        if self.proposed_by_id:
            is_teacher_identity = (
                getattr(self.proposed_by, "business_identity", None) == "TEACHER"
            )
            if not is_teacher_identity:
                raise ValidationError({"proposed_by": "Only teacher users can propose subjects."})

        if self.status == self.Status.ARCHIVED:
            self.is_archived = True
        elif self.is_archived and self.status != self.Status.ARCHIVED:
            raise ValidationError({"status": "Archived subject must use ARCHIVED status."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
