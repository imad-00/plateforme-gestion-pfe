from django.db import models
from django.utils import timezone


class AdminActionLog(models.Model):
    class ActionType(models.TextChoices):
        USER_IMPORT_PREVIEWED = "USER_IMPORT_PREVIEWED", "User Import Previewed"
        USER_IMPORT_COMPLETED = "USER_IMPORT_COMPLETED", "User Import Completed"
        USER_CREATED_BY_IMPORT = "USER_CREATED_BY_IMPORT", "User Created By Import"
        ACADEMIC_YEAR_CLOSED = "ACADEMIC_YEAR_CLOSED", "Academic Year Closed"
        ACADEMIC_YEAR_FORCE_CLOSED = "ACADEMIC_YEAR_FORCE_CLOSED", "Academic Year Force Closed"
        ACADEMIC_YEAR_REOPENED = "ACADEMIC_YEAR_REOPENED", "Academic Year Reopened"
        ACADEMIC_YEAR_ARCHIVED = "ACADEMIC_YEAR_ARCHIVED", "Academic Year Archived"
        USER_CREATED = "USER_CREATED", "User Created"
        USER_UPDATED = "USER_UPDATED", "User Updated"
        USER_ARCHIVED = "USER_ARCHIVED", "User Archived"
        PLATFORM_GRANT_CREATED = "PLATFORM_GRANT_CREATED", "Platform Grant Created"
        PLATFORM_GRANT_REVOKED = "PLATFORM_GRANT_REVOKED", "Platform Grant Revoked"
        TEAM_ADMIN_MODIFIED = "TEAM_ADMIN_MODIFIED", "Team Admin Modified"
        TEAM_DISSOLVED = "TEAM_DISSOLVED", "Team Dissolved"
        SUBJECT_APPROVED = "SUBJECT_APPROVED", "Subject Approved"
        SUBJECT_REJECTED = "SUBJECT_REJECTED", "Subject Rejected"
        ASSIGNMENT_RUN_BY_ADMIN = "ASSIGNMENT_RUN_BY_ADMIN", "Assignment Run By Admin"
        APPEAL_REVIEWED = "APPEAL_REVIEWED", "Appeal Reviewed"
        DEFENSE_SCHEDULED = "DEFENSE_SCHEDULED", "Defense Scheduled"
        DEFENSE_RESCHEDULED = "DEFENSE_RESCHEDULED", "Defense Rescheduled"
        DEFENSE_JURY_UPDATED = "DEFENSE_JURY_UPDATED", "Defense Jury Updated"
        DEFENSE_PV_UPLOADED = "DEFENSE_PV_UPLOADED", "Defense PV Uploaded"

    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="admin_action_logs",
    )
    action_type = models.CharField(max_length=64, choices=ActionType.choices)
    target_model = models.CharField(max_length=128, blank=True)
    target_id = models.CharField(max_length=128, blank=True)
    target_repr = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "audit_admin_action_log"
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["actor"], name="audit_admin_actor_idx"),
            models.Index(fields=["action_type"], name="audit_admin_action_idx"),
            models.Index(fields=["target_model"], name="audit_admin_target_model_idx"),
            models.Index(fields=["occurred_at"], name="audit_admin_occurred_idx"),
        ]

    def __str__(self):
        return f"{self.actor_id} - {self.action_type} - {self.target_model}:{self.target_id}"
