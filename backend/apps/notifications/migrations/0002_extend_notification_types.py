from django.db import migrations, models


# Choices-only change. CharField.max_length stays 64 (longest new value is
# CAMPAIGN_PHASE_CLOSING_SOON at 27 chars). The migration is recorded so the
# Django migration graph stays in sync with the model state.

NEW_TYPE_CHOICES = [
    ("TEAM_INVITATION_RECEIVED", "Team Invitation Received"),
    ("TEAM_MEMBER_JOINED", "Team Member Joined"),
    ("TEAM_MEMBER_LEFT", "Team Member Left"),
    ("TEAM_MEMBER_REMOVED", "Team Member Removed"),
    ("LEADERSHIP_TRANSFERRED", "Leadership Transferred"),
    ("TEAM_LOCKED", "Team Locked"),
    ("SUBJECT_SUBMITTED", "Subject Submitted"),
    ("SUBJECT_APPROVED", "Subject Approved"),
    ("SUBJECT_REJECTED", "Subject Rejected"),
    ("SUBJECT_RESUBMITTED", "Subject Resubmitted"),
    ("ASSIGNMENT_RESULT_AVAILABLE", "Assignment Result Available"),
    ("APPEAL_SUBMITTED", "Appeal Submitted"),
    ("APPEAL_ACCEPTED", "Appeal Accepted"),
    ("APPEAL_REJECTED", "Appeal Rejected"),
    ("DELIVERABLE_UPLOADED", "Deliverable Uploaded"),
    ("DELIVERABLE_REVIEWED", "Deliverable Reviewed"),
    ("DELIVERABLE_COMMENT_ADDED", "Deliverable Comment Added"),
    ("DEFENSE_REQUESTED", "Defense Requested"),
    ("DEFENSE_SUPERVISOR_ACCEPTED", "Defense Supervisor Accepted"),
    ("DEFENSE_SUPERVISOR_DENIED", "Defense Supervisor Denied"),
    ("DEFENSE_READY_TO_SCHEDULE", "Defense Ready To Schedule"),
    ("DEFENSE_SCHEDULED", "Defense Scheduled"),
    ("DEFENSE_RESCHEDULED", "Defense Rescheduled"),
    ("JURY_ASSIGNED", "Jury Assigned"),
    ("PV_UPLOADED", "PV Uploaded"),
    ("ACADEMIC_YEAR_CLOSED", "Academic Year Closed"),
    ("ACADEMIC_YEAR_FORCE_CLOSED", "Academic Year Force Closed"),
    ("ACADEMIC_YEAR_REOPENED", "Academic Year Reopened"),
    ("ACADEMIC_YEAR_ARCHIVED", "Academic Year Archived"),
    ("TEAM_INVITATION_REJECTED", "Team Invitation Rejected"),
    ("TEAM_DISSOLVED", "Team Dissolved"),
    ("TEAM_SUPERVISOR_ADDED", "Team Supervisor Added"),
    ("TEAM_SUPERVISOR_REMOVED", "Team Supervisor Removed"),
    ("SUBJECT_PENDING_MODERATION", "Subject Pending Moderation"),
    ("SUBJECT_ARCHIVED", "Subject Archived"),
    ("SUBJECT_ASSIGNED_TO_TEAM", "Subject Assigned To Team"),
    ("DEFENSE_CANCELLED", "Defense Cancelled"),
    ("DEFENSE_JURY_UPDATED", "Defense Jury Updated"),
    ("DEFENSE_FILES_UPDATED", "Defense Files Updated"),
    ("ACADEMIC_YEAR_OPENED", "Academic Year Opened"),
    ("CAMPAIGN_PHASE_OPENED", "Campaign Phase Opened"),
    ("CAMPAIGN_PHASE_CLOSED", "Campaign Phase Closed"),
    ("CAMPAIGN_PHASE_CLOSING_SOON", "Campaign Phase Closing Soon"),
    ("PLATFORM_GRANT_RECEIVED", "Platform Grant Received"),
    ("PLATFORM_GRANT_REVOKED", "Platform Grant Revoked"),
    ("PASSWORD_CHANGED", "Password Changed"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(choices=NEW_TYPE_CHOICES, max_length=64),
        ),
    ]
