from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        TEAM_INVITATION_RECEIVED = "TEAM_INVITATION_RECEIVED", "Team Invitation Received"
        TEAM_MEMBER_JOINED = "TEAM_MEMBER_JOINED", "Team Member Joined"
        TEAM_MEMBER_LEFT = "TEAM_MEMBER_LEFT", "Team Member Left"
        TEAM_MEMBER_REMOVED = "TEAM_MEMBER_REMOVED", "Team Member Removed"
        LEADERSHIP_TRANSFERRED = "LEADERSHIP_TRANSFERRED", "Leadership Transferred"
        TEAM_LOCKED = "TEAM_LOCKED", "Team Locked"
        SUBJECT_SUBMITTED = "SUBJECT_SUBMITTED", "Subject Submitted"
        SUBJECT_APPROVED = "SUBJECT_APPROVED", "Subject Approved"
        SUBJECT_REJECTED = "SUBJECT_REJECTED", "Subject Rejected"
        SUBJECT_RESUBMITTED = "SUBJECT_RESUBMITTED", "Subject Resubmitted"
        ASSIGNMENT_RESULT_AVAILABLE = "ASSIGNMENT_RESULT_AVAILABLE", "Assignment Result Available"
        APPEAL_SUBMITTED = "APPEAL_SUBMITTED", "Appeal Submitted"
        APPEAL_ACCEPTED = "APPEAL_ACCEPTED", "Appeal Accepted"
        APPEAL_REJECTED = "APPEAL_REJECTED", "Appeal Rejected"
        DELIVERABLE_UPLOADED = "DELIVERABLE_UPLOADED", "Deliverable Uploaded"
        DELIVERABLE_REVIEWED = "DELIVERABLE_REVIEWED", "Deliverable Reviewed"
        DELIVERABLE_COMMENT_ADDED = "DELIVERABLE_COMMENT_ADDED", "Deliverable Comment Added"
        DEFENSE_REQUESTED = "DEFENSE_REQUESTED", "Defense Requested"
        DEFENSE_SUPERVISOR_ACCEPTED = "DEFENSE_SUPERVISOR_ACCEPTED", "Defense Supervisor Accepted"
        DEFENSE_SUPERVISOR_DENIED = "DEFENSE_SUPERVISOR_DENIED", "Defense Supervisor Denied"
        DEFENSE_READY_TO_SCHEDULE = "DEFENSE_READY_TO_SCHEDULE", "Defense Ready To Schedule"
        DEFENSE_SCHEDULED = "DEFENSE_SCHEDULED", "Defense Scheduled"
        DEFENSE_RESCHEDULED = "DEFENSE_RESCHEDULED", "Defense Rescheduled"
        JURY_ASSIGNED = "JURY_ASSIGNED", "Jury Assigned"
        PV_UPLOADED = "PV_UPLOADED", "PV Uploaded"
        ACADEMIC_YEAR_CLOSED = "ACADEMIC_YEAR_CLOSED", "Academic Year Closed"
        ACADEMIC_YEAR_FORCE_CLOSED = "ACADEMIC_YEAR_FORCE_CLOSED", "Academic Year Force Closed"
        ACADEMIC_YEAR_REOPENED = "ACADEMIC_YEAR_REOPENED", "Academic Year Reopened"
        ACADEMIC_YEAR_ARCHIVED = "ACADEMIC_YEAR_ARCHIVED", "Academic Year Archived"
        # ─── Added in the 2026-05-30 gap-fill pass ───────────────────────────
        # Teams
        TEAM_INVITATION_REJECTED = "TEAM_INVITATION_REJECTED", "Team Invitation Rejected"
        TEAM_DISSOLVED = "TEAM_DISSOLVED", "Team Dissolved"
        TEAM_SUPERVISOR_ADDED = "TEAM_SUPERVISOR_ADDED", "Team Supervisor Added"
        TEAM_SUPERVISOR_REMOVED = "TEAM_SUPERVISOR_REMOVED", "Team Supervisor Removed"
        # Subjects
        SUBJECT_PENDING_MODERATION = "SUBJECT_PENDING_MODERATION", "Subject Pending Moderation"
        SUBJECT_ARCHIVED = "SUBJECT_ARCHIVED", "Subject Archived"
        SUBJECT_ASSIGNED_TO_TEAM = "SUBJECT_ASSIGNED_TO_TEAM", "Subject Assigned To Team"
        # Defenses
        DEFENSE_CANCELLED = "DEFENSE_CANCELLED", "Defense Cancelled"
        DEFENSE_JURY_UPDATED = "DEFENSE_JURY_UPDATED", "Defense Jury Updated"
        DEFENSE_FILES_UPDATED = "DEFENSE_FILES_UPDATED", "Defense Files Updated"
        # Academic year + phases
        ACADEMIC_YEAR_OPENED = "ACADEMIC_YEAR_OPENED", "Academic Year Opened"
        CAMPAIGN_PHASE_OPENED = "CAMPAIGN_PHASE_OPENED", "Campaign Phase Opened"
        CAMPAIGN_PHASE_CLOSED = "CAMPAIGN_PHASE_CLOSED", "Campaign Phase Closed"
        CAMPAIGN_PHASE_CLOSING_SOON = "CAMPAIGN_PHASE_CLOSING_SOON", "Campaign Phase Closing Soon"
        # Platform access + security
        PLATFORM_GRANT_RECEIVED = "PLATFORM_GRANT_RECEIVED", "Platform Grant Received"
        PLATFORM_GRANT_REVOKED = "PLATFORM_GRANT_REVOKED", "Platform Grant Revoked"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password Changed"

    class Importance(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        IMPORTANT = "IMPORTANT", "Important"

    id = models.BigAutoField(primary_key=True)
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    type = models.CharField(max_length=64, choices=Type.choices)
    importance = models.CharField(max_length=16, choices=Importance.choices, default=Importance.NORMAL)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "is_read"], name="notif_recipient_read_idx"),
            models.Index(fields=["type"], name="notif_type_idx"),
            models.Index(fields=["importance"], name="notif_importance_idx"),
            models.Index(fields=["created_at"], name="notif_created_idx"),
        ]

    def __str__(self):
        return f"{self.recipient_id} - {self.type} ({self.importance})"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    id = models.BigAutoField(primary_key=True)
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_delivery"
        indexes = [
            models.Index(fields=["notification"], name="notif_delivery_notif_idx"),
            models.Index(fields=["channel"], name="notif_delivery_channel_idx"),
            models.Index(fields=["status"], name="notif_delivery_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["notification", "channel"], name="notif_unique_delivery_channel"),
        ]

    def __str__(self):
        return f"{self.notification_id} - {self.channel} ({self.status})"
