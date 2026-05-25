from django.db.models import Case, Count, IntegerField, Q, When
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.academics.models import AcademicYear
from apps.accounts.models import User
from apps.accounts.permissions import get_platform_levels
from apps.assignments.models import Appeal
from apps.defenses.models import Defense, DefenseJuryAssignment, DefenseSupervisorDecision
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject


class DashboardService:
    @staticmethod
    def is_platform_admin(user):
        return bool(get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}))

    @staticmethod
    def serialize_academic_year(academic_year):
        return {
            "id": academic_year.id,
            "year": academic_year.year,
            "status": academic_year.status,
        }

    @staticmethod
    def serialize_user_name(user):
        if user is None:
            return ""
        return user.full_name or user.matricule or user.email or str(user.pk)

    @staticmethod
    def _active_academic_year():
        academic_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).order_by("-created_at").first()
        if academic_year is None:
            raise serializers.ValidationError({"academic_year": "No active academic year is configured."})
        return academic_year

    @staticmethod
    def _resolve_by_id(academic_year):
        if academic_year is None:
            return None
        if isinstance(academic_year, AcademicYear):
            return academic_year
        try:
            resolved = AcademicYear.objects.filter(pk=academic_year).first()
        except (TypeError, ValueError):
            resolved = None
        if resolved is None:
            raise serializers.ValidationError({"academic_year_id": "Academic year not found."})
        return resolved

    @staticmethod
    def resolve_academic_year_for_admin(user, academic_year=None):
        if not DashboardService.is_platform_admin(user):
            raise PermissionDenied("Only platform admins can access the admin dashboard.")
        resolved = DashboardService._resolve_by_id(academic_year)
        if resolved is not None:
            return resolved
        return DashboardService._active_academic_year()

    @staticmethod
    def assert_not_archived_for_non_admin(user, academic_year):
        if academic_year.status == AcademicYear.Status.ARCHIVED and not DashboardService.is_platform_admin(user):
            raise PermissionDenied("Archived academic-year data is available only to platform admins.")

    @staticmethod
    def _teacher_has_year_data(user, academic_year):
        return (
            TeamParticipant.objects.filter(
                user=user,
                role=TeamParticipant.Role.SUPERVISOR,
                team__academic_year=academic_year,
            ).exists()
            or Subject.objects.filter(proposed_by=user, academic_year=academic_year).exists()
            or DefenseJuryAssignment.objects.filter(user=user, defense__team__academic_year=academic_year).exists()
            or DefenseSupervisorDecision.objects.filter(
                supervisor=user,
                defense__team__academic_year=academic_year,
            ).exists()
        )

    @staticmethod
    def resolve_academic_year_for_teacher(user, academic_year=None):
        if user.business_identity not in {
            User.BusinessIdentity.TEACHER,
            User.BusinessIdentity.EXTERNAL_SUPERVISOR,
        } and not DashboardService.is_platform_admin(user):
            raise PermissionDenied("Only teachers, external supervisors, or platform admins can access this dashboard.")

        resolved = DashboardService._resolve_by_id(academic_year)
        if resolved is None:
            return DashboardService._active_academic_year()

        DashboardService.assert_not_archived_for_non_admin(user, resolved)
        if not DashboardService.is_platform_admin(user) and resolved.status == AcademicYear.Status.CLOSED:
            if not DashboardService._teacher_has_year_data(user, resolved):
                raise PermissionDenied("You do not have dashboard data in this academic year.")
        return resolved

    @staticmethod
    def _student_participations(user, academic_year=None):
        queryset = TeamParticipant.objects.select_related("team", "team__academic_year").filter(
            user=user,
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
        )
        if academic_year is not None:
            queryset = queryset.filter(team__academic_year=academic_year)
        return queryset.order_by(
            Case(
                When(status=TeamParticipant.Status.ACTIVE, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            "-joined_at",
            "-created_at",
        )

    @staticmethod
    def _student_has_year_data(user, academic_year):
        profile_year_id = getattr(getattr(user, "student_profile", None), "academic_year_id", None)
        return (
            profile_year_id == academic_year.id
            or TeamParticipant.objects.filter(
                user=user,
                role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
                team__academic_year=academic_year,
            ).exists()
        )

    @staticmethod
    def resolve_academic_year_for_student(user, academic_year=None):
        if user.business_identity != User.BusinessIdentity.STUDENT:
            raise PermissionDenied("Only students can access the student dashboard.")

        resolved = DashboardService._resolve_by_id(academic_year)
        if resolved is not None:
            DashboardService.assert_not_archived_for_non_admin(user, resolved)
            if not DashboardService._student_has_year_data(user, resolved):
                raise PermissionDenied("You do not have dashboard data in this academic year.")
            return resolved

        active_participation = DashboardService._student_participations(user).filter(
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        if active_participation is not None:
            DashboardService.assert_not_archived_for_non_admin(user, active_participation.team.academic_year)
            return active_participation.team.academic_year

        profile_year = getattr(getattr(user, "student_profile", None), "academic_year", None)
        if profile_year is not None:
            DashboardService.assert_not_archived_for_non_admin(user, profile_year)
            return profile_year

        return DashboardService._active_academic_year()

    @staticmethod
    def _status_counts(queryset, choices, key_map=None, field_name="status"):
        key_map = key_map or {}
        counts = {
            key_map.get(choice, choice.lower()): 0
            for choice, _label in choices
        }
        for row in queryset.values(field_name).annotate(total=Count("pk")):
            value = row[field_name]
            key = key_map.get(value, value.lower())
            counts[key] = row["total"]
        return counts

    @staticmethod
    def get_admin_dashboard(user, academic_year=None):
        academic_year = DashboardService.resolve_academic_year_for_admin(user, academic_year)
        teams = Team.objects.filter(academic_year=academic_year)
        defenses = Defense.objects.filter(team__academic_year=academic_year)
        appeals = Appeal.objects.filter(team__academic_year=academic_year)
        deliverables = DeliverableFile.objects.filter(team__academic_year=academic_year)
        subjects = Subject.objects.filter(academic_year=academic_year)

        team_counts = DashboardService._status_counts(teams, Team.Status.choices)
        defense_counts = DashboardService._status_counts(defenses, Defense.Status.choices)
        appeal_counts = DashboardService._status_counts(appeals, Appeal.Status.choices)
        deliverable_counts = DashboardService._status_counts(
            deliverables,
            DeliverableFile.ReviewStatus.choices,
            key_map={
                DeliverableFile.ReviewStatus.PENDING: "pending_review",
                DeliverableFile.ReviewStatus.NEEDS_REVISION: "needs_revision",
            },
            field_name="review_status",
        )
        subject_counts = DashboardService._status_counts(subjects, Subject.Status.choices)

        return {
            "academic_year": DashboardService.serialize_academic_year(academic_year),
            "teams": {
                "total": teams.count(),
                "forming": team_counts.get("forming", 0),
                "locked": team_counts.get("locked", 0),
                "validated": team_counts.get("validated", 0),
                "dissolved": team_counts.get("dissolved", 0),
            },
            "assignments": {
                "assigned": teams.filter(selected_subject__isnull=False).count(),
                "unassigned": teams.filter(selected_subject__isnull=True).count(),
            },
            "defenses": {
                "total": defenses.count(),
                "requested": defense_counts.get("requested", 0),
                "ready_to_schedule": defense_counts.get("ready_to_schedule", 0),
                "scheduled": defense_counts.get("scheduled", 0),
                "completed": defense_counts.get("completed", 0),
                "cancelled": defense_counts.get("cancelled", 0),
            },
            "appeals": {
                "total": appeals.count(),
                "pending_or_submitted": appeal_counts.get("pending", 0),
                "accepted": appeal_counts.get("accepted", 0),
                "rejected": appeal_counts.get("rejected", 0),
            },
            "deliverables": {
                "total_files": deliverables.count(),
                "pending_review": deliverable_counts.get("pending_review", 0),
                "accepted": deliverable_counts.get("accepted", 0),
                "needs_revision": deliverable_counts.get("needs_revision", 0),
                "rejected": deliverable_counts.get("rejected", 0),
            },
            "subjects": {
                "total": subjects.count(),
                "draft": subject_counts.get("draft", 0),
                "submitted": subject_counts.get("submitted", 0),
                "approved": subject_counts.get("approved", 0),
                "assigned": subject_counts.get("assigned", 0),
                "rejected": subject_counts.get("rejected", 0),
            },
        }

    @staticmethod
    def _supervised_teams(user, academic_year):
        return Team.objects.filter(
            academic_year=academic_year,
            participants__user=user,
            participants__role=TeamParticipant.Role.SUPERVISOR,
            participants__status=TeamParticipant.Status.ACTIVE,
        ).distinct()

    @staticmethod
    def get_teacher_dashboard(user, academic_year=None):
        academic_year = DashboardService.resolve_academic_year_for_teacher(user, academic_year)
        now = timezone.now()
        supervised_teams = DashboardService._supervised_teams(user, academic_year)

        pending_deliverables = DeliverableFile.objects.filter(
            team__in=supervised_teams,
            review_status=DeliverableFile.ReviewStatus.PENDING,
        ).select_related("team", "uploaded_by").order_by("-uploaded_at", "-created_at")
        latest_pending = [
            {
                "file_id": str(deliverable.pk),
                "original_filename": deliverable.original_filename,
                "team_code": deliverable.team_id,
                "uploaded_at": deliverable.uploaded_at.isoformat() if deliverable.uploaded_at else "",
                "uploaded_by": DashboardService.serialize_user_name(deliverable.uploaded_by),
            }
            for deliverable in pending_deliverables[:5]
        ]

        supervised_upcoming = Defense.objects.filter(
            team__in=supervised_teams,
            status=Defense.Status.SCHEDULED,
            scheduled_at__gte=now,
        )
        jury_upcoming = Defense.objects.filter(
            jury_assignments__user=user,
            team__academic_year=academic_year,
            status=Defense.Status.SCHEDULED,
            scheduled_at__gte=now,
        )
        upcoming = (
            (supervised_upcoming | jury_upcoming)
            .select_related("team")
            .distinct()
            .order_by("scheduled_at", "team_id", "id")
        )
        supervised_ids = set(supervised_teams.values_list("pk", flat=True))
        upcoming_items = []
        for defense in upcoming[:5]:
            role_context = "SUPERVISOR" if defense.team_id in supervised_ids else "JURY"
            if role_context == "SUPERVISOR" and DefenseJuryAssignment.objects.filter(defense=defense, user=user).exists():
                role_context = "SUPERVISOR,JURY"
            upcoming_items.append(
                {
                    "defense_id": str(defense.pk),
                    "team_code": defense.team_id,
                    "team_name": defense.team.name,
                    "scheduled_at": defense.scheduled_at.isoformat() if defense.scheduled_at else "",
                    "location": defense.location or "",
                    "role_context": role_context,
                }
            )

        pending_requests_count = DefenseSupervisorDecision.objects.filter(
            supervisor=user,
            decision=DefenseSupervisorDecision.DecisionStatus.PENDING,
            defense__team__academic_year=academic_year,
        ).count()

        return {
            "academic_year": DashboardService.serialize_academic_year(academic_year),
            "supervision": {
                "supervised_teams_count": supervised_teams.count(),
                "validated_supervised_teams_count": supervised_teams.filter(status=Team.Status.VALIDATED).count(),
            },
            "deliverables": {
                "pending_review_count": pending_deliverables.count(),
                "latest_pending_review": latest_pending,
            },
            "defenses": {
                "upcoming_count": upcoming.count(),
                "pending_requests_count": pending_requests_count,
                "upcoming": upcoming_items,
            },
        }

    @staticmethod
    def _serialize_participants(team, roles):
        return [
            {
                "id": participant.user_id,
                "name": DashboardService.serialize_user_name(participant.user),
                "role": participant.role,
            }
            for participant in team.participants.all()
            if participant.status == TeamParticipant.Status.ACTIVE and participant.role in roles
        ]

    @staticmethod
    def _selected_student_participation(user, academic_year):
        return DashboardService._student_participations(user, academic_year).first()

    @staticmethod
    def get_student_dashboard(user, academic_year=None):
        academic_year = DashboardService.resolve_academic_year_for_student(user, academic_year)
        participation = DashboardService._selected_student_participation(user, academic_year)
        team = None
        if participation is not None:
            team = (
                Team.objects.filter(pk=participation.team_id)
                .select_related("academic_year", "selected_subject")
                .prefetch_related("participants__user")
                .first()
            )

        subject = team.selected_subject if team else None
        defense = None
        latest_deliverables = []
        total_files = 0
        if team is not None:
            defense = (
                Defense.objects.filter(team=team)
                .order_by("-requested_at", "-created_at")
                .first()
            )
            files = DeliverableFile.objects.filter(team=team).select_related("uploaded_by").order_by("-uploaded_at", "-created_at")
            total_files = files.count()
            latest_deliverables = [
                {
                    "file_id": str(deliverable.pk),
                    "original_filename": deliverable.original_filename,
                    "uploaded_at": deliverable.uploaded_at.isoformat() if deliverable.uploaded_at else "",
                    "uploaded_by": DashboardService.serialize_user_name(deliverable.uploaded_by),
                    "review_status": deliverable.review_status,
                }
                for deliverable in files[:5]
            ]

        return {
            "academic_year": DashboardService.serialize_academic_year(academic_year),
            "team": None
            if team is None
            else {
                "team_code": team.pk,
                "name": team.name,
                "status": team.status,
                "role": participation.role,
                "members": DashboardService._serialize_participants(
                    team,
                    {TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER},
                ),
                "supervisors": DashboardService._serialize_participants(
                    team,
                    {TeamParticipant.Role.SUPERVISOR},
                ),
            },
            "subject": None
            if subject is None
            else {
                "id": subject.id,
                "title": subject.title,
                "type": subject.subject_type,
                "status": subject.status,
            },
            "defense": None
            if defense is None
            else {
                "id": str(defense.pk),
                "status": defense.status,
                "scheduled_at": defense.scheduled_at.isoformat() if defense.scheduled_at else "",
                "location": defense.location or "",
                "final_grade": str(defense.final_grade) if defense.final_grade is not None else "",
                "pv_uploaded": bool(defense.pv_uploaded_at or defense.pv_file),
            },
            "deliverables": {
                "total_files": total_files,
                "latest": latest_deliverables,
            },
            "assignment": {
                "selection_round": team.selection_round if team else "",
                "assigned": subject is not None,
            },
        }
