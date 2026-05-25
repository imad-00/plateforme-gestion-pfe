from django.utils import timezone
from rest_framework import serializers

from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase


class CampaignPhaseService:
    """Centralized phase-window checks for campaign-bound actions."""

    PHASE_MESSAGES = {
        CampaignPhase.PhaseType.TEAM_FORMATION: "The team formation phase is not open.",
        CampaignPhase.PhaseType.SUBJECT_MANAGEMENT: "The subject management phase is not open.",
        CampaignPhase.PhaseType.WISHLIST_1: "The first wishlist phase is not open.",
        CampaignPhase.PhaseType.WISHLIST_2: "The second wishlist phase is not open.",
        CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1: "The first assignment review phase is not open.",
        CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_2: "The second assignment review phase is not open.",
        CampaignPhase.PhaseType.RESULTS_AND_APPEALS: "The results and appeals phase is not open.",
        CampaignPhase.PhaseType.WORK_AND_SUPERVISION: "The work and supervision phase is not open.",
        CampaignPhase.PhaseType.DEFENSE_WINDOW: "The defense window phase is not open.",
    }

    @staticmethod
    def get_active_academic_year():
        return AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()

    @staticmethod
    def is_open(academic_year, phase_type, at_time=None):
        if academic_year is None or academic_year.status != AcademicYear.Status.ACTIVE:
            return False
        now = at_time or timezone.now()
        return CampaignPhase.objects.filter(
            academic_year=academic_year,
            phase_type=phase_type,
            is_archived=False,
            start_at__lte=now,
        ).filter(end_at__isnull=True).exists() or CampaignPhase.objects.filter(
            academic_year=academic_year,
            phase_type=phase_type,
            is_archived=False,
            start_at__lte=now,
            end_at__gte=now,
        ).exists()

    @staticmethod
    def require_open(academic_year, phase_type, at_time=None):
        if academic_year is None:
            raise serializers.ValidationError({"academic_year": "No active academic year is configured."})
        if not CampaignPhaseService.is_open(academic_year, phase_type, at_time=at_time):
            message = CampaignPhaseService.PHASE_MESSAGES.get(phase_type, f"The {phase_type} phase is not open.")
            raise serializers.ValidationError({"phase": message})

    @staticmethod
    def get_open_phases(academic_year):
        if academic_year is None or academic_year.status != AcademicYear.Status.ACTIVE:
            return []
        now = timezone.now()
        open_phase_types = set(
            CampaignPhase.objects.filter(
                academic_year=academic_year,
                is_archived=False,
                start_at__lte=now,
            )
            .filter(end_at__isnull=True)
            .values_list("phase_type", flat=True)
        )
        open_phase_types.update(
            CampaignPhase.objects.filter(
                academic_year=academic_year,
                is_archived=False,
                start_at__lte=now,
                end_at__gte=now,
            ).values_list("phase_type", flat=True)
        )
        return sorted(open_phase_types)

    @staticmethod
    def get_user_action_availability(user):
        from apps.assignments.models import Appeal
        from apps.teams.models import Team
        from apps.teams.services import TeamService

        academic_year = CampaignPhaseService.get_active_academic_year()
        team = TeamService.get_active_student_team(user) if user and user.is_authenticated else None
        effective_year = getattr(team, "academic_year", None) or academic_year
        open_phases = CampaignPhaseService.get_open_phases(effective_year)
        has_accepted_appeal = False
        if team is not None:
            has_accepted_appeal = Appeal.objects.filter(team=team, status=Appeal.Status.ACCEPTED).exists()

        actions = {
            "can_manage_team": CampaignPhase.PhaseType.TEAM_FORMATION in open_phases,
            "can_submit_first_wishlist": CampaignPhase.PhaseType.WISHLIST_1 in open_phases,
            "can_view_subject_catalog": CampaignPhase.PhaseType.WISHLIST_1 in open_phases
            or (CampaignPhase.PhaseType.WISHLIST_2 in open_phases and has_accepted_appeal),
            "can_run_first_assignment": CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1 in open_phases,
            "can_view_assignment_result": CampaignPhase.PhaseType.RESULTS_AND_APPEALS in open_phases,
            "can_submit_appeal": CampaignPhase.PhaseType.RESULTS_AND_APPEALS in open_phases,
            "can_submit_second_wishlist": CampaignPhase.PhaseType.WISHLIST_2 in open_phases
            and has_accepted_appeal
            and team is not None
            and team.selection_round == Team.SelectionRound.SECOND,
        }
        return {
            "academic_year": None
            if effective_year is None
            else {"id": effective_year.id, "label": effective_year.year, "status": effective_year.status},
            "open_phases": open_phases,
            "actions": actions,
        }
