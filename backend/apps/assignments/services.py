from decimal import Decimal
import random

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.permissions import get_platform_levels
from apps.academics.models import AcademicYear
from apps.assignments.models import Appeal, WishItem, WishList
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


class AssignmentPermissionMixin:
    @staticmethod
    def ensure_platform_admin(user):
        if not get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}):
            raise serializers.ValidationError({"detail": "Platform admin access is required."})


class SubjectCompatibilityService:
    @staticmethod
    def active_student_count(team):
        return TeamService.count_active_student_members(team)

    @staticmethod
    def is_subject_compatible(team, subject):
        student_count = SubjectCompatibilityService.active_student_count(team)
        if student_count > 2:
            return subject.subject_type == Subject.SubjectType.STARTUP_PROJECT
        return True

    @staticmethod
    def ensure_subject_compatible(team, subject):
        if not SubjectCompatibilityService.is_subject_compatible(team, subject):
            raise serializers.ValidationError(
                {"subject": "Teams with more than 2 students can choose only STARTUP_PROJECT subjects."}
            )


class WishListService:
    @staticmethod
    def _wishlist_phase_for_round(selection_round):
        if selection_round == Team.SelectionRound.SECOND:
            return CampaignPhase.PhaseType.WISHLIST_2
        return CampaignPhase.PhaseType.WISHLIST_1

    @staticmethod
    def ensure_catalog_open_for_team(team):
        if CampaignPhaseService.is_open(team.academic_year, CampaignPhase.PhaseType.WISHLIST_1):
            return
        if CampaignPhaseService.is_open(team.academic_year, CampaignPhase.PhaseType.WISHLIST_2):
            try:
                appeal = team.appeal
            except Appeal.DoesNotExist:
                appeal = None
            if (
                appeal is not None
                and appeal.status == Appeal.Status.ACCEPTED
                and team.selection_round == Team.SelectionRound.SECOND
            ):
                return
        raise serializers.ValidationError(
            {"phase": "The subject catalog is not currently open for your team."}
        )

    @staticmethod
    def get_available_subjects_for_user_without_team():
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        if active_year is None:
            return Subject.objects.none()
        return Subject.objects.filter(
            academic_year=active_year,
            status=Subject.Status.APPROVED,
            assigned_to_team__isnull=True,
        ).select_related("proposed_by", "academic_year")

    @staticmethod
    def get_available_subjects_for_team(team):
        queryset = Subject.objects.filter(
            academic_year=team.academic_year,
            status=Subject.Status.APPROVED,
            assigned_to_team__isnull=True,
        ).select_related("proposed_by", "academic_year")

        if SubjectCompatibilityService.active_student_count(team) > 2:
            queryset = queryset.filter(subject_type=Subject.SubjectType.STARTUP_PROJECT)
        return queryset

    @staticmethod
    def _ensure_active_leader(team, actor):
        if not TeamParticipant.objects.filter(
            team=team,
            user=actor,
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).exists():
            raise serializers.ValidationError({"detail": "Only the active team leader can perform this action."})

    @staticmethod
    def _ensure_second_round_allowed(team):
        try:
            appeal = team.appeal
        except Appeal.DoesNotExist:
            appeal = None
        if appeal is None or appeal.status != Appeal.Status.ACCEPTED:
            raise serializers.ValidationError(
                {"selection_round": "SECOND round wishlist is allowed only after an accepted appeal."}
            )

    @staticmethod
    def validate_subject_choices(team, subjects, selection_round):
        if selection_round == Team.SelectionRound.SECOND:
            WishListService._ensure_second_round_allowed(team)

        available_queryset = WishListService.get_available_subjects_for_team(team)
        available_ids = set(available_queryset.values_list("id", flat=True))
        selected_ids = [subject.id for subject in subjects]

        if not selected_ids:
            raise serializers.ValidationError({"items": "Wishlist cannot be empty."})
        if len(selected_ids) != len(set(selected_ids)):
            raise serializers.ValidationError({"items": "The same subject cannot appear twice in one wishlist."})

        unavailable_ids = [subject_id for subject_id in selected_ids if subject_id not in available_ids]
        if unavailable_ids:
            raise serializers.ValidationError(
                {"items": "Wishlist contains unavailable or incompatible subjects."}
            )
        if any(subject.academic_year_id != team.academic_year_id for subject in subjects):
            raise serializers.ValidationError(
                {"items": "All wishlist subjects must belong to the same academic year as the team."}
            )

        configured_size = team.academic_year.wishlist_size
        required_size = min(configured_size, available_queryset.count())
        if required_size == 0:
            raise serializers.ValidationError({"items": "No compatible subjects are currently available."})
        if len(subjects) > configured_size:
            raise serializers.ValidationError({"items": f"Wishlist cannot exceed {configured_size} subjects."})
        if len(subjects) != required_size:
            raise serializers.ValidationError(
                {"items": f"Wishlist must contain exactly {required_size} subject(s) for this round."}
            )

    @staticmethod
    @transaction.atomic
    def submit_wishlist(team, actor, selection_round, items):
        team = Team.objects.select_for_update().select_related("academic_year").get(pk=team.pk)
        list(TeamParticipant.objects.select_for_update().filter(team=team, status=TeamParticipant.Status.ACTIVE))
        WishListService._ensure_active_leader(team, actor)
        CampaignPhaseService.require_open(team.academic_year, WishListService._wishlist_phase_for_round(selection_round))

        if team.status not in {Team.Status.FORMING, Team.Status.LOCKED}:
            raise serializers.ValidationError({"team": "Wishlist can be submitted only by FORMING or LOCKED teams."})
        if selection_round != team.selection_round:
            raise serializers.ValidationError({"selection_round": "Wishlist round must match the team's current round."})
        if selection_round == Team.SelectionRound.SECOND and team.status != Team.Status.LOCKED:
            raise serializers.ValidationError({"team": "Second wishlist can be submitted only by LOCKED teams."})
        if WishList.objects.filter(team=team, selection_round=selection_round).exists():
            raise serializers.ValidationError({"selection_round": "This team already submitted a wishlist for this round."})

        ranks = [item["rank"] for item in items]
        if len(ranks) != len(set(ranks)):
            raise serializers.ValidationError({"items": "Wishlist ranks must be unique."})
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise serializers.ValidationError({"items": "Wishlist ranks must be continuous from 1 to N."})

        subject_ids = [item["subject_id"] for item in items]
        subjects_by_id = Subject.objects.in_bulk(subject_ids)
        if len(subjects_by_id) != len(set(subject_ids)):
            raise serializers.ValidationError({"items": "One or more subjects do not exist."})

        ordered_subjects = [subjects_by_id[subject_id] for subject_id in subject_ids]
        WishListService.validate_subject_choices(team, ordered_subjects, selection_round)
        if team.status == Team.Status.FORMING:
            if TeamService.count_active_leaders(team) != 1:
                raise serializers.ValidationError({"team": "Team must have exactly one active leader before locking."})
            TeamService.ensure_team_size_limit(team)
            team.status = Team.Status.LOCKED
            team.save(update_fields=["status", "updated_at"])

        try:
            wishlist = WishList.objects.create(
                team=team,
                academic_year=team.academic_year,
                selection_round=selection_round,
                status=WishList.Status.SUBMITTED,
                submitted_by=actor,
                submitted_at=timezone.now(),
            )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"selection_round": "This team already submitted a wishlist for this round."}
            ) from exc

        WishItem.objects.bulk_create(
            [
                WishItem(
                    wishlist=wishlist,
                    subject=subjects_by_id[item["subject_id"]],
                    rank=item["rank"],
                )
                for item in items
            ]
        )
        return wishlist


class AssignmentService(AssignmentPermissionMixin):
    @staticmethod
    def _assignment_phase_for_round(selection_round):
        if selection_round == Team.SelectionRound.SECOND:
            return CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_2
        return CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1

    @staticmethod
    def compute_team_average(team):
        values = []
        participants = team.participants.select_related("user", "user__student_profile").filter(
            status=TeamParticipant.Status.ACTIVE,
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
        )
        for participant in participants:
            profile = getattr(participant.user, "student_profile", None)
            average = getattr(profile, "annual_average", None)
            values.append(Decimal(average) if average is not None else Decimal("10.00"))

        if not values:
            team.annual_average = None
        else:
            team.annual_average = sum(values) / Decimal(len(values))
        team.save(update_fields=["annual_average", "updated_at"])
        return team.annual_average

    @staticmethod
    def _eligible_locked_teams(selection_round):
        submitted_team_ids = WishList.objects.filter(
            selection_round=selection_round,
            status=WishList.Status.SUBMITTED,
        ).values("team_id")
        return (
            Team.objects.select_for_update()
            .select_related("academic_year")
            .filter(
                pk__in=submitted_team_ids,
                status=Team.Status.LOCKED,
                selection_round=selection_round,
            )
        )

    @staticmethod
    def _wishlist_for_team(team, selection_round):
        return (
            WishList.objects.select_related("team")
            .prefetch_related("items__subject")
            .get(team=team, selection_round=selection_round, status=WishList.Status.SUBMITTED)
        )

    @staticmethod
    def _assign_first_available_wished_subject(team, selection_round, admin_user):
        wishlist = AssignmentService._wishlist_for_team(team, selection_round)
        for item in wishlist.items.select_related("subject").order_by("rank"):
            subject = item.subject
            if subject.status != Subject.Status.APPROVED or subject.assigned_to_team_id is not None:
                continue
            if not SubjectCompatibilityService.is_subject_compatible(team, subject):
                continue
            return AssignmentService.assign_subject_to_team(team, subject, admin_user)
        return None

    @staticmethod
    def _empty_summary(mode, selection_round):
        return {
            "mode": mode,
            "selection_round": selection_round,
            "assigned_teams": [],
            "unassigned_teams": [],
            "skipped_teams": [],
        }

    @staticmethod
    @transaction.atomic
    def assign_by_merit(admin_user, selection_round, seed=None):
        AssignmentService.ensure_platform_admin(admin_user)
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        CampaignPhaseService.require_open(active_year, AssignmentService._assignment_phase_for_round(selection_round))
        rng = random.Random(seed)
        summary = AssignmentService._empty_summary("MERIT_AVERAGE", selection_round)
        eligible = [
            team for team in AssignmentService._eligible_locked_teams(selection_round)
            if active_year is not None and team.academic_year_id == active_year.id
        ]

        ranked = []
        for team in eligible:
            average = AssignmentService.compute_team_average(team)
            if average is None:
                summary["skipped_teams"].append({"team_code": team.pk, "reason": "no_active_student_members"})
                continue
            ranked.append((team, average, rng.random()))

        ranked.sort(key=lambda item: (-item[1], item[2]))
        for team, average, _tie_breaker in ranked:
            assigned = AssignmentService._assign_first_available_wished_subject(team, selection_round, admin_user)
            if assigned is None:
                summary["unassigned_teams"].append({"team_code": team.pk, "reason": "no_available_wished_subject"})
            else:
                summary["assigned_teams"].append(
                    {"team_code": team.pk, "subject_id": assigned.selected_subject.id, "annual_average": str(average)}
                )
        return summary

    @staticmethod
    @transaction.atomic
    def assign_randomly(admin_user, selection_round, seed=None):
        AssignmentService.ensure_platform_admin(admin_user)
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        CampaignPhaseService.require_open(active_year, AssignmentService._assignment_phase_for_round(selection_round))
        rng = random.Random(seed)
        summary = AssignmentService._empty_summary("RANDOM", selection_round)
        eligible = [
            team for team in AssignmentService._eligible_locked_teams(selection_round)
            if active_year is not None and team.academic_year_id == active_year.id
        ]
        rng.shuffle(eligible)

        for team in eligible:
            AssignmentService.compute_team_average(team)
            assigned = AssignmentService._assign_first_available_wished_subject(team, selection_round, admin_user)
            if assigned is None:
                summary["unassigned_teams"].append({"team_code": team.pk, "reason": "no_available_wished_subject"})
            else:
                summary["assigned_teams"].append({"team_code": team.pk, "subject_id": assigned.selected_subject.id})
        return summary

    @staticmethod
    @transaction.atomic
    def manual_assign(admin_user, team, subject):
        AssignmentService.ensure_platform_admin(admin_user)
        CampaignPhaseService.require_open(team.academic_year, AssignmentService._assignment_phase_for_round(team.selection_round))
        return AssignmentService.assign_subject_to_team(team, subject, admin_user)

    @staticmethod
    @transaction.atomic
    def assign_subject_to_team(team, subject, admin_user):
        team = Team.objects.select_for_update().get(pk=team.pk)
        subject = Subject.objects.select_for_update().get(pk=subject.pk)

        if team.status != Team.Status.LOCKED:
            raise serializers.ValidationError({"team": "Only LOCKED teams can receive a subject assignment."})
        if team.academic_year_id != subject.academic_year_id:
            raise serializers.ValidationError({"academic_year": "Team and subject must belong to the same academic year."})
        if Subject.objects.filter(assigned_to_team=team).exists():
            raise serializers.ValidationError({"team": "This team already has an assigned subject."})
        if subject.status != Subject.Status.APPROVED:
            raise serializers.ValidationError({"subject": "Only APPROVED subjects can be assigned."})
        if subject.assigned_to_team_id is not None:
            raise serializers.ValidationError({"subject": "This subject is already assigned to another team."})

        SubjectCompatibilityService.ensure_subject_compatible(team, subject)

        subject.status = Subject.Status.ASSIGNED
        subject.assigned_to_team = team
        subject.assigned_at = timezone.now()
        subject.save(update_fields=["status", "assigned_to_team", "assigned_at", "updated_at"])

        team.assignment_validated_at = None
        team.assignment_validated_by = None
        team.save(update_fields=["assignment_validated_at", "assignment_validated_by", "updated_at"])
        team.refresh_from_db()
        return team

    @staticmethod
    @transaction.atomic
    def validate_assignment(admin_user, team):
        AssignmentService.ensure_platform_admin(admin_user)
        team = Team.objects.select_for_update().get(pk=team.pk)
        CampaignPhaseService.require_open(team.academic_year, AssignmentService._assignment_phase_for_round(team.selection_round))
        if team.status != Team.Status.LOCKED:
            raise serializers.ValidationError({"team": "Only LOCKED teams can be assignment-validated."})
        subject = Subject.objects.select_for_update().filter(assigned_to_team=team).first()
        if subject is None or subject.status != Subject.Status.ASSIGNED:
            raise serializers.ValidationError({"team": "Team has no reserved assigned subject to validate."})
        team.status = Team.Status.VALIDATED
        team.assignment_validated_at = timezone.now()
        team.assignment_validated_by = admin_user
        team.save(update_fields=["status", "assignment_validated_at", "assignment_validated_by", "updated_at"])
        TeamService.ensure_subject_owner_supervisor(team, subject)
        team.refresh_from_db()
        from apps.notifications.services import NotificationService

        NotificationService.notify_assignment_result_available(team, actor=admin_user)
        return team


class AppealService(AssignmentPermissionMixin):
    @staticmethod
    @transaction.atomic
    def submit_appeal(team, actor, reason):
        team = Team.objects.select_for_update().get(pk=team.pk)
        CampaignPhaseService.require_open(team.academic_year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS)
        WishListService._ensure_active_leader(team, actor)
        clean_reason = (reason or "").strip()
        if not clean_reason:
            raise serializers.ValidationError({"reason": "Appeal reason is required."})
        if team.status != Team.Status.VALIDATED:
            raise serializers.ValidationError({"team": "Appeal can be submitted only after a first assignment."})
        if team.selection_round != Team.SelectionRound.FIRST:
            raise serializers.ValidationError({"team": "Appeal is allowed only after FIRST round assignment."})
        if not Subject.objects.filter(assigned_to_team=team, status=Subject.Status.ASSIGNED).exists():
            raise serializers.ValidationError({"team": "Team has no assigned subject to appeal."})
        if Appeal.objects.filter(team=team).exists():
            raise serializers.ValidationError({"team": "This team already submitted an appeal."})

        appeal = Appeal.objects.create(
            team=team,
            reason=clean_reason,
            status=Appeal.Status.PENDING,
            submitted_by=actor,
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_appeal_submitted(appeal, actor=actor)
        return appeal

    @staticmethod
    @transaction.atomic
    def accept_appeal(appeal, admin_user):
        AppealService.ensure_platform_admin(admin_user)
        appeal = Appeal.objects.select_for_update().select_related("team").get(pk=appeal.pk)
        team = Team.objects.select_for_update().get(pk=appeal.team_id)
        CampaignPhaseService.require_open(team.academic_year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS)
        if appeal.status != Appeal.Status.PENDING:
            raise serializers.ValidationError({"appeal": "Only PENDING appeals can be accepted."})

        subject = Subject.objects.select_for_update().filter(assigned_to_team=team).first()
        if subject is None:
            raise serializers.ValidationError({"team": "Team has no assigned subject to release."})

        subject.status = Subject.Status.APPROVED
        subject.assigned_to_team = None
        subject.assigned_at = None
        subject.save(update_fields=["status", "assigned_to_team", "assigned_at", "updated_at"])

        team.status = Team.Status.LOCKED
        team.selection_round = Team.SelectionRound.SECOND
        team.assignment_validated_at = None
        team.assignment_validated_by = None
        team.save(update_fields=["status", "selection_round", "assignment_validated_at", "assignment_validated_by", "updated_at"])

        appeal.status = Appeal.Status.ACCEPTED
        appeal.reviewed_by = admin_user
        appeal.resolved_at = timezone.now()
        appeal.save(update_fields=["status", "reviewed_by", "resolved_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_appeal_decision(appeal, accepted=True, actor=admin_user)
        return appeal

    @staticmethod
    @transaction.atomic
    def reject_appeal(appeal, admin_user, admin_comment=""):
        AppealService.ensure_platform_admin(admin_user)
        appeal = Appeal.objects.select_for_update().get(pk=appeal.pk)
        CampaignPhaseService.require_open(appeal.team.academic_year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS)
        if appeal.status != Appeal.Status.PENDING:
            raise serializers.ValidationError({"appeal": "Only PENDING appeals can be rejected."})

        appeal.status = Appeal.Status.REJECTED
        appeal.reviewed_by = admin_user
        appeal.resolved_at = timezone.now()
        appeal.admin_comment = (admin_comment or "").strip()
        appeal.save(update_fields=["status", "reviewed_by", "resolved_at", "admin_comment", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_appeal_decision(appeal, accepted=False, actor=admin_user)
        return appeal
