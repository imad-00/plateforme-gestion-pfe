from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject


MAX_PRE_ASSIGNMENT_STUDENTS = 7


class TeamService:
    @staticmethod
    def lock_user(user):
        return User.objects.select_for_update().get(pk=user.pk)

    @staticmethod
    def get_active_academic_year():
        return AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()

    @staticmethod
    def get_active_student_participation(user):
        return (
            TeamParticipant.objects.select_related("team", "user")
            .filter(
                user=user,
                status=TeamParticipant.Status.ACTIVE,
                role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            )
            .exclude(team__status__in=[Team.Status.DISSOLVED, Team.Status.ARCHIVED])
            .exclude(team__academic_year__status=AcademicYear.Status.ARCHIVED)
            .order_by("-joined_at", "-created_at")
            .first()
        )

    @staticmethod
    def lock_student_participations(user):
        return list(
            TeamParticipant.objects.select_for_update()
            .select_related("team")
            .filter(
                user=user,
                status=TeamParticipant.Status.ACTIVE,
                role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            )
            .exclude(team__status__in=[Team.Status.DISSOLVED, Team.Status.ARCHIVED])
            .exclude(team__academic_year__status=AcademicYear.Status.ARCHIVED)
        )

    @staticmethod
    def get_active_student_team(user):
        participation = TeamService.get_active_student_participation(user)
        return participation.team if participation else None

    @staticmethod
    def count_active_student_members(team):
        return team.participants.filter(
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        ).count()

    @staticmethod
    def count_active_leaders(team):
        return team.participants.filter(
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).count()

    @staticmethod
    def assert_operational_team_has_exactly_one_leader(team):
        if team.status in {Team.Status.DISSOLVED, Team.Status.ARCHIVED}:
            return
        leader_count = TeamService.count_active_leaders(team)
        if leader_count != 1:
            raise serializers.ValidationError({"team": "Operational team must have exactly one active leader."})

    @staticmethod
    def dissolve_if_no_active_students(team, actor=None):
        team.refresh_from_db()
        if team.status in {Team.Status.DISSOLVED, Team.Status.ARCHIVED}:
            return team
        if TeamService.count_active_student_members(team) == 0:
            return TeamService.dissolve_team(team, actor=actor)
        return team

    @staticmethod
    def is_solo_team_for_user(team, user):
        active_students = list(
            team.participants.filter(
                role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
                status=TeamParticipant.Status.ACTIVE,
            )
        )
        return (
            team.status == Team.Status.FORMING
            and len(active_students) == 1
            and active_students[0].user_id == user.id
            and active_students[0].role == TeamParticipant.Role.LEADER
        )

    @staticmethod
    def ensure_student(user):
        if getattr(user, "business_identity", None) != User.BusinessIdentity.STUDENT:
            raise serializers.ValidationError({"user": "Only Student users can be team members."})
        if user.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError({"user": "Only ACTIVE students can participate in teams."})

    @staticmethod
    def ensure_team_can_be_modified_by_student(team):
        if team.status != Team.Status.FORMING:
            raise serializers.ValidationError({"team": "Students can modify only FORMING teams."})
        CampaignPhaseService.require_open(team.academic_year, CampaignPhase.PhaseType.TEAM_FORMATION)

    @staticmethod
    def ensure_team_can_be_modified_by_admin(team):
        from apps.archives.services import AcademicYearLifecycleService

        AcademicYearLifecycleService.assert_academic_year_writable(team.academic_year)
        if team.status == Team.Status.ARCHIVED:
            raise serializers.ValidationError({"team": "Archived teams cannot be modified."})

    @staticmethod
    def ensure_team_size_limit(team, extra_students=0):
        current_count = TeamService.count_active_student_members(team)
        if current_count + extra_students > MAX_PRE_ASSIGNMENT_STUDENTS:
            raise serializers.ValidationError(
                {"team": f"Team cannot exceed {MAX_PRE_ASSIGNMENT_STUDENTS} active students before assignment."}
            )

    @staticmethod
    @transaction.atomic
    def create_solo_team_for_student(student, academic_year=None):
        student = TeamService.lock_user(student)
        TeamService.ensure_student(student)
        TeamService.lock_student_participations(student)
        existing = TeamService.get_active_student_participation(student)
        if existing:
            return existing.team

        if academic_year is None:
            profile = getattr(student, "student_profile", None)
            academic_year = getattr(profile, "academic_year", None) or TeamService.get_active_academic_year()
        if academic_year is None:
            raise serializers.ValidationError({"academic_year": "No active academic year is configured."})
        if academic_year.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError({"academic_year": "Solo team must belong to the active academic year."})
        profile = getattr(student, "student_profile", None)
        if profile is not None:
            if profile.academic_year_id and profile.academic_year_id != academic_year.id:
                raise serializers.ValidationError(
                    {"academic_year": "Team academic year must match the student's academic year."}
                )
            if profile.academic_year_id is None:
                profile.academic_year = academic_year
                profile.save(update_fields=["academic_year", "updated_at"])

        team = Team.objects.create(
            academic_year=academic_year,
            name=f"{student.matricule} Solo Team",
            status=Team.Status.FORMING,
            selection_round=Team.SelectionRound.FIRST,
        )
        TeamParticipant.objects.create(
            team=team,
            user=student,
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
            joined_at=timezone.now(),
        )
        return team

    @staticmethod
    @transaction.atomic
    def dissolve_team(team, actor=None, reason=None):
        team = Team.objects.select_for_update().get(pk=team.pk)
        from apps.archives.services import AcademicYearLifecycleService

        AcademicYearLifecycleService.assert_academic_year_writable(team.academic_year)
        if team.status in {Team.Status.DISSOLVED, Team.Status.ARCHIVED}:
            return team
        # Snapshot active participants BEFORE we end them so the notification
        # actually reaches the people who lost their team.
        affected_users = list(
            User.objects.filter(
                team_participations__team=team,
                team_participations__status=TeamParticipant.Status.ACTIVE,
            ).distinct()
        )
        now = timezone.now()
        team.status = Team.Status.DISSOLVED
        team.dissolved_at = now
        team.save(update_fields=["status", "dissolved_at", "updated_at"])
        team.participants.filter(status__in=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.PENDING]).update(
            status=TeamParticipant.Status.ENDED,
            ended_at=now,
            updated_at=now,
        )
        if affected_users:
            from apps.notifications.services import NotificationService

            NotificationService.notify_team_dissolved(team, affected_users, actor=actor)
        return team

    @staticmethod
    def _active_leader_participation(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()

    @staticmethod
    @transaction.atomic
    def lock_team(team, actor):
        team = Team.objects.select_for_update().get(pk=team.pk)
        TeamService.ensure_team_can_be_modified_by_student(team)
        if not TeamService._active_leader_participation(team, actor):
            raise serializers.ValidationError({"detail": "Only the active leader can lock this team."})
        if TeamService.count_active_leaders(team) != 1:
            raise serializers.ValidationError({"team": "Team must have exactly one active leader."})
        if TeamService.count_active_student_members(team) < 1:
            raise serializers.ValidationError({"team": "Team must have at least one active student participant."})
        TeamService.ensure_team_size_limit(team)
        TeamService.assert_operational_team_has_exactly_one_leader(team)
        team.status = Team.Status.LOCKED
        team.save(update_fields=["status", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_locked(team, actor=actor)
        return team

    @staticmethod
    @transaction.atomic
    def ensure_subject_owner_supervisor(team, subject):
        owner = subject.proposed_by
        if owner.business_identity != User.BusinessIdentity.TEACHER:
            return None
        team = Team.objects.select_for_update().get(pk=team.pk)
        participant, _ = TeamParticipant.objects.get_or_create(
            team=team,
            user=owner,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
            defaults={"joined_at": timezone.now()},
        )
        return participant


class InvitationService:
    @staticmethod
    def _resolve_invitable_student(user):
        TeamService.ensure_student(user)
        TeamService.lock_student_participations(user)
        active = TeamService.get_active_student_participation(user)
        if active and not TeamService.is_solo_team_for_user(active.team, user):
            raise serializers.ValidationError({"student": "Student already belongs to an active team."})
        return user

    @staticmethod
    @transaction.atomic
    def invite_student(team, invited_user, actor):
        team = Team.objects.select_for_update().get(pk=team.pk)
        TeamService.ensure_team_can_be_modified_by_student(team)
        if not TeamService._active_leader_participation(team, actor):
            raise serializers.ValidationError({"detail": "Only the active leader can invite students."})
        TeamService.assert_operational_team_has_exactly_one_leader(team)
        invited_user = InvitationService._resolve_invitable_student(invited_user)
        if team.participants.filter(
            user=invited_user,
            status__in=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.PENDING],
        ).exists():
            raise serializers.ValidationError({"student": "Student already has an active or pending participation in this team."})
        TeamService.ensure_team_size_limit(team, extra_students=1)
        participation = TeamParticipant.objects.create(
            team=team,
            user=invited_user,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.PENDING,
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_invitation_received(participation, actor=actor)
        return participation

    @staticmethod
    @transaction.atomic
    def accept_invitation(participation, actor):
        participation = TeamParticipant.objects.select_for_update().select_related("team", "user").get(pk=participation.pk)
        Team.objects.select_for_update().get(pk=participation.team_id)
        if participation.user_id != actor.id:
            raise serializers.ValidationError({"detail": "Only the invited user can accept this invitation."})
        if participation.status != TeamParticipant.Status.PENDING or participation.role != TeamParticipant.Role.MEMBER:
            raise serializers.ValidationError({"invitation": "Only pending member invitations can be accepted."})
        TeamService.ensure_team_can_be_modified_by_student(participation.team)
        TeamService.assert_operational_team_has_exactly_one_leader(participation.team)
        TeamService.lock_student_participations(actor)
        active = TeamService.get_active_student_participation(actor)
        if active and not TeamService.is_solo_team_for_user(active.team, actor):
            raise serializers.ValidationError({"student": "Student already belongs to an active team."})
        TeamService.ensure_team_size_limit(participation.team, extra_students=1)

        if active and TeamService.is_solo_team_for_user(active.team, actor):
            TeamService.dissolve_team(active.team, actor=actor)

        participation.status = TeamParticipant.Status.ACTIVE
        participation.joined_at = timezone.now()
        participation.save(update_fields=["status", "joined_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_member_joined(participation.team, actor, actor=actor)
        return participation

    @staticmethod
    @transaction.atomic
    def reject_invitation(participation, actor):
        participation = TeamParticipant.objects.select_for_update().select_related("team", "user").get(pk=participation.pk)
        CampaignPhaseService.require_open(participation.team.academic_year, CampaignPhase.PhaseType.TEAM_FORMATION)
        if participation.user_id != actor.id:
            raise serializers.ValidationError({"detail": "Only the invited user can reject this invitation."})
        if participation.status != TeamParticipant.Status.PENDING:
            raise serializers.ValidationError({"invitation": "Only pending invitations can be rejected."})
        participation.status = TeamParticipant.Status.REJECTED
        participation.ended_at = timezone.now()
        participation.save(update_fields=["status", "ended_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_invitation_rejected(participation, actor=actor)
        return participation


class ParticipationService:
    @staticmethod
    @transaction.atomic
    def leave_team(actor):
        TeamService.lock_student_participations(actor)
        participation = TeamService.get_active_student_participation(actor)
        if not participation:
            raise serializers.ValidationError({"team": "You do not have an active team membership."})
        team = Team.objects.select_for_update().get(pk=participation.team_id)
        TeamService.ensure_team_can_be_modified_by_student(team)
        if participation.role == TeamParticipant.Role.LEADER:
            raise serializers.ValidationError({"team": "Leader must transfer leadership before leaving."})

        now = timezone.now()
        participation.status = TeamParticipant.Status.ENDED
        participation.ended_at = now
        participation.save(update_fields=["status", "ended_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_member_left(team, actor, actor=actor)
        TeamService.create_solo_team_for_student(actor, academic_year=team.academic_year)
        TeamService.dissolve_if_no_active_students(team, actor=actor)
        return participation

    @staticmethod
    @transaction.atomic
    def remove_member(team, target_user, actor):
        team = Team.objects.select_for_update().get(pk=team.pk)
        TeamService.lock_student_participations(target_user)
        TeamService.ensure_team_can_be_modified_by_student(team)
        if not TeamService._active_leader_participation(team, actor):
            raise serializers.ValidationError({"detail": "Only the active leader can remove members."})
        TeamService.assert_operational_team_has_exactly_one_leader(team)
        target_participation = TeamParticipant.objects.filter(
            team=team,
            user=target_user,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        if not target_participation:
            raise serializers.ValidationError({"student": "Target user is not an active member of this team."})
        now = timezone.now()
        target_participation.status = TeamParticipant.Status.ENDED
        target_participation.ended_at = now
        target_participation.save(update_fields=["status", "ended_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_member_removed(team, target_user, actor=actor)
        TeamService.create_solo_team_for_student(target_user, academic_year=team.academic_year)
        return target_participation

    @staticmethod
    @transaction.atomic
    def transfer_leadership(team, new_leader_user, actor, *, admin_override=False):
        team = Team.objects.select_for_update().get(pk=team.pk)
        list(TeamParticipant.objects.select_for_update().filter(team=team, status=TeamParticipant.Status.ACTIVE))
        if admin_override:
            TeamService.ensure_team_can_be_modified_by_admin(team)
        else:
            TeamService.ensure_team_can_be_modified_by_student(team)
            if not TeamService._active_leader_participation(team, actor):
                raise serializers.ValidationError({"detail": "Only the active leader can transfer leadership."})

        old_leader = TeamParticipant.objects.filter(
            team=team,
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        new_leader = TeamParticipant.objects.filter(
            team=team,
            user=new_leader_user,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        if not old_leader:
            raise serializers.ValidationError({"team": "Team has no active leader."})
        if not new_leader:
            raise serializers.ValidationError({"new_leader": "New leader must be an active member of the same team."})

        old_leader_user = old_leader.user
        old_leader.role = TeamParticipant.Role.MEMBER
        old_leader.save(update_fields=["role", "updated_at"])
        new_leader.role = TeamParticipant.Role.LEADER
        new_leader.save(update_fields=["role", "updated_at"])
        TeamService.assert_operational_team_has_exactly_one_leader(team)
        from apps.notifications.services import NotificationService

        NotificationService.notify_leadership_transferred(team, new_leader.user, old_leader=old_leader_user, actor=actor)
        return team

    @staticmethod
    @transaction.atomic
    def admin_remove_member(team, target_user, actor, new_leader_user=None, dissolve_if_needed=False):
        team = Team.objects.select_for_update().get(pk=team.pk)
        list(TeamParticipant.objects.select_for_update().filter(team=team, status=TeamParticipant.Status.ACTIVE))
        TeamService.lock_student_participations(target_user)
        TeamService.ensure_team_can_be_modified_by_admin(team)
        target = TeamParticipant.objects.filter(
            team=team,
            user=target_user,
            status=TeamParticipant.Status.ACTIVE,
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
        ).first()
        if not target:
            raise serializers.ValidationError({"student": "Target user is not an active student participant of this team."})

        if target.role == TeamParticipant.Role.LEADER:
            if dissolve_if_needed:
                dissolved_team = TeamService.dissolve_team(team, actor=actor)
                TeamService.create_solo_team_for_student(target_user, academic_year=team.academic_year)
                return dissolved_team
            if new_leader_user is None:
                raise serializers.ValidationError({"new_leader_id": "Removing a leader requires a new leader or dissolution."})
            ParticipationService.transfer_leadership(team, new_leader_user, actor, admin_override=True)
            target.refresh_from_db()

        now = timezone.now()
        target.status = TeamParticipant.Status.ENDED
        target.ended_at = now
        target.save(update_fields=["status", "ended_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_member_removed(team, target_user, actor=actor)
        remaining_students = TeamService.count_active_student_members(team)
        if remaining_students == 0:
            TeamService.dissolve_team(team, actor=actor)
        else:
            TeamService.assert_operational_team_has_exactly_one_leader(team)
        TeamService.create_solo_team_for_student(target_user, academic_year=team.academic_year)
        return target

    @staticmethod
    @transaction.atomic
    def add_supervisor(team, supervisor_user, actor):
        team = Team.objects.select_for_update().get(pk=team.pk)
        list(
            TeamParticipant.objects.select_for_update().filter(
                team=team,
                user=supervisor_user,
                role=TeamParticipant.Role.SUPERVISOR,
                status=TeamParticipant.Status.ACTIVE,
            )
        )
        TeamService.ensure_team_can_be_modified_by_admin(team)
        if supervisor_user.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError({"user": "Supervisor account must be ACTIVE."})
        if supervisor_user.business_identity not in {User.BusinessIdentity.TEACHER, User.BusinessIdentity.EXTERNAL_SUPERVISOR}:
            raise serializers.ValidationError({"user": "Supervisor must be a Teacher or ExternalSupervisor."})
        participant, created = TeamParticipant.objects.get_or_create(
            team=team,
            user=supervisor_user,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
            defaults={"joined_at": timezone.now()},
        )
        if created:
            from apps.notifications.services import NotificationService

            NotificationService.notify_team_supervisor_added(team, supervisor_user, actor=actor)
        return participant

    @staticmethod
    @transaction.atomic
    def remove_supervisor(team, supervisor_user, actor):
        team = Team.objects.select_for_update().get(pk=team.pk)
        list(TeamParticipant.objects.select_for_update().filter(team=team, status=TeamParticipant.Status.ACTIVE))
        TeamService.ensure_team_can_be_modified_by_admin(team)
        participant = TeamParticipant.objects.filter(
            team=team,
            user=supervisor_user,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        if not participant:
            raise serializers.ValidationError({"user": "User is not an active supervisor of this team."})
        participant.status = TeamParticipant.Status.ENDED
        participant.ended_at = timezone.now()
        participant.save(update_fields=["status", "ended_at", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_team_supervisor_removed(team, supervisor_user, actor=actor)
        return participant
