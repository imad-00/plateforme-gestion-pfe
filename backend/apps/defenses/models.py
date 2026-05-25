import uuid
from pathlib import Path

from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename


def defense_pv_upload_to(instance, filename):
    safe_name = get_valid_filename(Path(filename).name or "pv")
    return f"defenses/{instance.team.academic_year_id}/{instance.team_id}/pv/{safe_name}"


class Defense(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        READY_TO_SCHEDULE = "READY_TO_SCHEDULE", "Ready To Schedule"
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.PROTECT,
        related_name="defenses",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUESTED)
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="requested_defenses",
    )
    requested_at = models.DateTimeField()
    scheduled_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    scheduled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="scheduled_defenses",
        null=True,
        blank=True,
    )
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    deliberation = models.TextField(blank=True)
    pv_file = models.FileField(upload_to=defense_pv_upload_to, null=True, blank=True)
    pv_uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="pv_uploaded_defenses",
        null=True,
        blank=True,
    )
    pv_uploaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "defenses_defense"
        ordering = ["-requested_at", "-created_at"]
        indexes = [
            models.Index(fields=["team"], name="def_team_idx"),
            models.Index(fields=["status"], name="def_status_idx"),
            models.Index(fields=["scheduled_at"], name="def_sched_idx"),
        ]

    def __str__(self):
        return f"{self.team_id} ({self.status})"


class DefenseAttachedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defense = models.ForeignKey(
        "defenses.Defense",
        on_delete=models.PROTECT,
        related_name="attached_files",
    )
    deliverable_file = models.ForeignKey(
        "deliverables.DeliverableFile",
        on_delete=models.PROTECT,
        related_name="defense_links",
    )
    order = models.PositiveIntegerField()
    added_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="added_defense_files",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "defenses_attached_file"
        ordering = ["order", "added_at"]
        constraints = [
            models.UniqueConstraint(fields=["defense", "deliverable_file"], name="def_unique_attached_file"),
            models.UniqueConstraint(fields=["defense", "order"], name="def_unique_attached_order"),
        ]
        indexes = [
            models.Index(fields=["defense"], name="def_att_def_idx"),
            models.Index(fields=["deliverable_file"], name="def_att_file_idx"),
        ]

    def __str__(self):
        return f"{self.defense_id} - {self.deliverable_file_id}"


class DefenseSupervisorDecision(models.Model):
    class DecisionStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DENIED = "DENIED", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defense = models.ForeignKey(
        "defenses.Defense",
        on_delete=models.PROTECT,
        related_name="supervisor_decisions",
    )
    supervisor = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="defense_supervisor_decisions",
    )
    decision = models.CharField(max_length=16, choices=DecisionStatus.choices, default=DecisionStatus.PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "defenses_supervisor_decision"
        constraints = [
            models.UniqueConstraint(fields=["defense", "supervisor"], name="def_unique_supervisor_decision"),
        ]
        indexes = [
            models.Index(fields=["defense"], name="def_sup_dec_def_idx"),
            models.Index(fields=["supervisor"], name="def_sup_dec_user_idx"),
            models.Index(fields=["decision"], name="def_sup_dec_status_idx"),
        ]

    def __str__(self):
        return f"{self.defense_id} - {self.supervisor_id} ({self.decision})"


class DefenseJuryAssignment(models.Model):
    class JuryRole(models.TextChoices):
        PRESIDENT = "PRESIDENT", "President"
        EXAMINER = "EXAMINER", "Examiner"
        GUEST = "GUEST", "Guest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defense = models.ForeignKey(
        "defenses.Defense",
        on_delete=models.PROTECT,
        related_name="jury_assignments",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="defense_jury_assignments",
    )
    role = models.CharField(max_length=16, choices=JuryRole.choices)
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="assigned_defense_jury_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "defenses_jury_assignment"
        constraints = [
            models.UniqueConstraint(fields=["defense", "user"], name="def_unique_jury_user"),
        ]
        indexes = [
            models.Index(fields=["defense"], name="def_jury_def_idx"),
            models.Index(fields=["user"], name="def_jury_user_idx"),
            models.Index(fields=["role"], name="def_jury_role_idx"),
        ]

    def __str__(self):
        return f"{self.defense_id} - {self.user_id} ({self.role})"
