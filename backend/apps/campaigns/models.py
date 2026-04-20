from django.core.exceptions import ValidationError
from django.db import models


class CampaignPhase(models.Model):
    class PhaseType(models.TextChoices):
        ACCOUNT_SETUP = "ACCOUNT_SETUP", "Account Setup"
        SUBJECT_SUBMISSION_AND_REVIEW = "SUBJECT_SUBMISSION_AND_REVIEW", "Subject Submission and Review"
        FIRST_WISH_SELECTION = "FIRST_WISH_SELECTION", "First Wish Selection"
        RESULTS_AND_APPEALS = "RESULTS_AND_APPEALS", "Results and Appeals"
        SECOND_WISH_SELECTION = "SECOND_WISH_SELECTION", "Second Wish Selection"
        FINAL_RESULTS_AND_ASSIGNMENT = "FINAL_RESULTS_AND_ASSIGNMENT", "Final Results and Assignment"
        WORK_PERIOD = "WORK_PERIOD", "Work Period"
        DEFENSE_PERIOD = "DEFENSE_PERIOD", "Defense Period"

    id = models.BigAutoField(primary_key=True)
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.CASCADE,
        related_name="campaign_phases",
    )
    phase_type = models.CharField(max_length=50, choices=PhaseType.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=1)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns_campaign_phase"
        ordering = ["academic_year", "display_order", "start_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "phase_type"],
                name="campaigns_unique_phase_type_per_year",
            ),
            models.UniqueConstraint(
                fields=["academic_year", "display_order"],
                name="campaigns_unique_phase_order_per_year",
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year"], name="campaigns_phase_year_idx"),
            models.Index(fields=["phase_type"], name="campaigns_phase_type_idx"),
            models.Index(fields=["is_archived"], name="campaigns_phase_archived_idx"),
        ]

    def __str__(self):
        return f"{self.academic_year.year} - {self.phase_type}"

    def clean(self):
        if self.academic_year.is_archived:
            raise ValidationError({"academic_year": "Cannot attach phase to archived academic year."})

        if self.end_at is not None and self.end_at < self.start_at:
            raise ValidationError({"end_at": "end_at must be greater than or equal to start_at."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
