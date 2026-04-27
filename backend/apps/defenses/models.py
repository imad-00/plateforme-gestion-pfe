import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Defense(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"
        ARCHIVED = "ARCHIVED", "Archived"

    defense_code = models.CharField(max_length=32, primary_key=True)
    team = models.OneToOneField(
        "teams.Team",
        on_delete=models.PROTECT,
        related_name="defense",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="defenses",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    room = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    pv_file_url = models.CharField(max_length=500, blank=True)
    final_grade = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "defenses_defense"
        indexes = [
            models.Index(fields=["academic_year"], name="defense_year_idx"),
            models.Index(fields=["status"], name="defense_status_idx"),
        ]


class DefenseJuryAssignment(models.Model):
    class JuryRole(models.TextChoices):
        PRESIDENT = "PRESIDENT", "President"
        EXAMINER = "EXAMINER", "Examiner"
        GUEST = "GUEST", "Guest"

    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defense = models.ForeignKey(
        "defenses.Defense",
        on_delete=models.CASCADE,
        related_name="jury_assignments",
    )
    juror = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="defense_jury_assignments",
    )
    jury_role = models.CharField(max_length=16, choices=JuryRole.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "defenses_jury_assignment"
        indexes = [
            models.Index(fields=["defense"], name="jury_defense_idx"),
            models.Index(fields=["jury_role"], name="jury_role_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["defense"],
                condition=Q(jury_role="PRESIDENT"),
                name="defense_single_president",
            )
        ]

    def clean(self):
        from apps.teams.models import TeamParticipant

        is_supervisor = TeamParticipant.objects.filter(
            team=self.defense.team,
            user=self.juror,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
        ).exists()

        if is_supervisor and self.jury_role == self.JuryRole.PRESIDENT:
            raise ValidationError(
                {"juror": "A team supervisor cannot be PRESIDENT of the same team's defense jury."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
