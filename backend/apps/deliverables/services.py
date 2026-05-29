from pathlib import Path

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.deliverables.models import DeliverableFile, DeliverableFileComment
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService


class DeliverableFileService:
    @staticmethod
    def _active_supervisor_participation(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
        ).first()

    @staticmethod
    def _active_student_participation_for_team(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        ).first()

    @staticmethod
    def _ensure_uploadable_team(team):
        if team is None:
            raise serializers.ValidationError({"team": "You do not have an active team."})
        if team.status != Team.Status.VALIDATED:
            raise serializers.ValidationError({"team": "Only VALIDATED teams can upload work files."})
        if not hasattr(team, "selected_subject"):
            raise serializers.ValidationError({"team": "Team must have an assigned subject before uploading files."})

    @staticmethod
    def _extract_file_metadata(uploaded_file):
        original_filename = Path(uploaded_file.name).name or "deliverable"
        file_size = getattr(uploaded_file, "size", 0) or 0
        content_type = getattr(uploaded_file, "content_type", "") or ""
        return original_filename, file_size, content_type

    @staticmethod
    def list_team_files(user):
        team = TeamService.get_active_student_team(user)
        if team is None or team.status != Team.Status.VALIDATED:
            return DeliverableFile.objects.none()
        return DeliverableFile.objects.select_related("team", "uploaded_by", "reviewed_by").prefetch_related(
            "comments__author"
        ).filter(team=team)

    @staticmethod
    @transaction.atomic
    def upload_file(actor, uploaded_file, comment=None):
        actor = TeamService.lock_user(actor)
        participation = TeamService.get_active_student_participation(actor)
        team = participation.team if participation else None
        DeliverableFileService._ensure_uploadable_team(team)
        if participation is None or participation.role not in {
            TeamParticipant.Role.LEADER,
            TeamParticipant.Role.MEMBER,
        }:
            raise serializers.ValidationError({"detail": "Only active team members can upload work files."})
        CampaignPhaseService.require_open(team.academic_year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION)
        original_filename, file_size, content_type = DeliverableFileService._extract_file_metadata(uploaded_file)
        deliverable_file = DeliverableFile.objects.create(
            team=team,
            file=uploaded_file,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            uploaded_by=actor,
            comment=(comment or "").strip(),
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_deliverable_uploaded(deliverable_file, actor=actor)
        return deliverable_file

    @staticmethod
    def list_supervised_teams(supervisor_user):
        return (
            Team.objects.filter(
                participants__user=supervisor_user,
                participants__role=TeamParticipant.Role.SUPERVISOR,
                participants__status=TeamParticipant.Status.ACTIVE,
                status=Team.Status.VALIDATED,
            )
            .exclude(academic_year__status="ARCHIVED")
            .select_related("academic_year")
            .prefetch_related("participants__user", "deliverable_files")
            .distinct()
        )

    @staticmethod
    def list_files_for_supervised_team(supervisor_user, team):
        from apps.archives.services import AcademicYearLifecycleService

        AcademicYearLifecycleService.assert_archived_access_allowed(supervisor_user, team.academic_year)
        if DeliverableFileService._active_supervisor_participation(team, supervisor_user) is None:
            raise serializers.ValidationError({"detail": "You do not supervise this team."})
        return DeliverableFile.objects.select_related("team", "uploaded_by", "reviewed_by").prefetch_related(
            "comments__author"
        ).filter(team=team)

    @staticmethod
    def can_access_file(user, deliverable_file):
        from apps.archives.services import AcademicYearLifecycleService

        if not user or getattr(user, "account_status", None) != User.AccountStatus.ACTIVE:
            return False
        if not AcademicYearLifecycleService.can_access_archived_year(user, deliverable_file.team.academic_year):
            return False
        if DeliverableFileService._active_student_participation_for_team(deliverable_file.team, user) is not None:
            return True
        if DeliverableFileService._active_supervisor_participation(deliverable_file.team, user) is not None:
            return True
        return False

    @staticmethod
    def _ensure_comment_author(team, user):
        if DeliverableFileService._active_student_participation_for_team(team, user) is not None:
            return
        if DeliverableFileService._active_supervisor_participation(team, user) is not None:
            return
        raise serializers.ValidationError({"detail": "Only active team members or supervisors can comment on this file."})

    @staticmethod
    @transaction.atomic
    def review_file(supervisor_user, deliverable_file, review_status, review_comment=None):
        deliverable_file = (
            DeliverableFile.objects.select_for_update()
            .select_related("team", "team__academic_year")
            .get(pk=deliverable_file.pk)
        )
        if DeliverableFileService._active_supervisor_participation(deliverable_file.team, supervisor_user) is None:
            raise serializers.ValidationError({"detail": "Only active supervisors can review this file."})
        CampaignPhaseService.require_open(
            deliverable_file.team.academic_year,
            CampaignPhase.PhaseType.WORK_AND_SUPERVISION,
        )
        if review_status not in {
            DeliverableFile.ReviewStatus.ACCEPTED,
            DeliverableFile.ReviewStatus.NEEDS_REVISION,
            DeliverableFile.ReviewStatus.REJECTED,
        }:
            raise serializers.ValidationError({"review_status": "Invalid review status."})
        deliverable_file.review_status = review_status
        deliverable_file.reviewed_by = supervisor_user
        deliverable_file.reviewed_at = timezone.now()
        deliverable_file.review_comment = (review_comment or "").strip()
        deliverable_file.save(
            update_fields=[
                "review_status",
                "reviewed_by",
                "reviewed_at",
                "review_comment",
                "updated_at",
            ]
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_deliverable_reviewed(deliverable_file, actor=supervisor_user)
        return deliverable_file

    @staticmethod
    @transaction.atomic
    def add_comment(author, deliverable_file, text):
        author = TeamService.lock_user(author)
        deliverable_file = DeliverableFile.objects.select_for_update().select_related("team").get(pk=deliverable_file.pk)
        from apps.archives.services import AcademicYearLifecycleService

        AcademicYearLifecycleService.assert_academic_year_writable(deliverable_file.team.academic_year)
        DeliverableFileService._ensure_comment_author(deliverable_file.team, author)
        CampaignPhaseService.require_open(
            deliverable_file.team.academic_year,
            CampaignPhase.PhaseType.WORK_AND_SUPERVISION,
        )
        comment = DeliverableFileComment.objects.create(
            deliverable_file=deliverable_file,
            author=author,
            text=text.strip(),
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_deliverable_comment_added(comment, actor=author)
        return comment
