import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def generate_team_code():
    return f"TEAM-{uuid.uuid4().hex[:10].upper()}"


class Team(models.Model):
    class Status(models.TextChoices):
        FORMING = "FORMING", "Forming"
        LOCKED = "LOCKED", "Locked"
        VALIDATED = "VALIDATED", "Validated"
        DISSOLVED = "DISSOLVED", "Dissolved"
        ARCHIVED = "ARCHIVED", "Archived"

    class SelectionRound(models.TextChoices):
        FIRST = "FIRST", "First"
        SECOND = "SECOND", "Second"

    team_code = models.CharField(max_length=32, primary_key=True, default=generate_team_code, editable=False)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.FORMING)
    selection_round = models.CharField(
        max_length=8,
        choices=SelectionRound.choices,
        default=SelectionRound.FIRST,
    )
    annual_average = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="teams",
    )
    assignment_validated_at = models.DateTimeField(null=True, blank=True)
    assignment_validated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="validated_team_assignments",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    dissolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "teams_team"
        indexes = [
            models.Index(fields=["status"], name="teams_team_status_idx"),
            models.Index(fields=["academic_year"], name="teams_team_year_idx"),
        ]

    def __str__(self):
        return f"{self.team_code} - {self.name}"

    @property
    def is_operational(self):
        return self.status not in {self.Status.DISSOLVED, self.Status.ARCHIVED}

    def active_student_participants(self):
        return self.participants.filter(
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        )


class TeamParticipant(models.Model):
    class Role(models.TextChoices):
        LEADER = "LEADER", "Leader"
        MEMBER = "MEMBER", "Member"
        SUPERVISOR = "SUPERVISOR", "Supervisor"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"
        REJECTED = "REJECTED", "Rejected"

    participation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="team_participations",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    joined_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_team_participant"
        indexes = [
            models.Index(fields=["team"], name="teams_part_team_idx"),
            models.Index(fields=["user"], name="teams_part_user_idx"),
            models.Index(fields=["role"], name="teams_part_role_idx"),
            models.Index(fields=["status"], name="teams_part_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=Q(role="LEADER", status="ACTIVE"),
                name="teams_one_active_leader_per_team",
            ),
            models.UniqueConstraint(
                fields=["team", "user", "role"],
                condition=Q(status="ACTIVE"),
                name="teams_unique_active_user_role_per_team",
            ),
            models.UniqueConstraint(
                fields=["team", "user"],
                condition=Q(status="PENDING", role="MEMBER"),
                name="teams_unique_pending_member_invite",
            ),
            models.UniqueConstraint(
                fields=["team", "user"],
                condition=Q(status="ACTIVE", role="SUPERVISOR"),
                name="teams_unique_active_supervisor",
            ),
        ]

    def __str__(self):
        return f"{self.team_id} - {self.user_id} - {self.role}"

    def clean(self):
        identity = getattr(self.user, "business_identity", None)
        if self.role in {self.Role.LEADER, self.Role.MEMBER} and identity != "STUDENT":
            raise ValidationError({"role": "LEADER/MEMBER roles are allowed only for Student users."})
        if self.role == self.Role.SUPERVISOR and identity not in {"TEACHER", "EXTERNAL_SUPERVISOR"}:
            raise ValidationError({"role": "SUPERVISOR role is allowed only for Teacher or ExternalSupervisor users."})

        # One active student participation per academic year.
        if (
            self.status == self.Status.ACTIVE
            and self.role in {self.Role.LEADER, self.Role.MEMBER}
            and identity == "STUDENT"
        ):
            existing = TeamParticipant.objects.filter(
                user=self.user,
                status=self.Status.ACTIVE,
                role__in=[self.Role.LEADER, self.Role.MEMBER],
                team__academic_year=self.team.academic_year,
            ).exclude(team__status__in=["DISSOLVED", "ARCHIVED"])
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    {"user": "A student can have only one active team participation in the same academic year."}
                )

        if self.status == self.Status.ACTIVE and self.joined_at is None:
            self.joined_at = timezone.now()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
