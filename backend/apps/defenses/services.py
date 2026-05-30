from pathlib import Path

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.permissions import get_platform_levels
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.defenses.models import Defense, DefenseAttachedFile, DefenseJuryAssignment, DefenseSupervisorDecision
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService


class DefenseService:
    ACTIVE_DEFENSE_STATUSES = {
        Defense.Status.REQUESTED,
        Defense.Status.READY_TO_SCHEDULE,
        Defense.Status.SCHEDULED,
    }

    @staticmethod
    def _ensure_platform_admin(user):
        if not get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}):
            raise serializers.ValidationError({"detail": "Platform admin access is required."})

    @staticmethod
    def _require_defense_window(academic_year):
        CampaignPhaseService.require_open(academic_year, CampaignPhase.PhaseType.DEFENSE_WINDOW)

    @staticmethod
    def _active_leader_participation(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()

    @staticmethod
    def _active_member_or_leader(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        ).exists()

    @staticmethod
    def _active_supervisors(team):
        return list(
            TeamParticipant.objects.select_related("user").filter(
                team=team,
                role=TeamParticipant.Role.SUPERVISOR,
                status=TeamParticipant.Status.ACTIVE,
            )
        )

    @staticmethod
    def _ensure_team_ready_for_defense_request(team):
        if team is None:
            raise serializers.ValidationError({"team": "You do not have an active team."})
        if team.status != Team.Status.VALIDATED:
            raise serializers.ValidationError({"team": "Only VALIDATED teams can request a defense."})
        if not hasattr(team, "selected_subject"):
            raise serializers.ValidationError({"team": "Team must have an assigned subject before requesting defense."})

    @staticmethod
    def _ensure_no_active_defense(team):
        if Defense.objects.filter(team=team, status__in=DefenseService.ACTIVE_DEFENSE_STATUSES).exists():
            raise serializers.ValidationError({"team": "This team already has an active defense workflow."})

    @staticmethod
    def _extract_file_metadata(uploaded_file):
        original_filename = Path(uploaded_file.name).name or "deliverable"
        file_size = getattr(uploaded_file, "size", 0) or 0
        content_type = getattr(uploaded_file, "content_type", "") or ""
        return original_filename, file_size, content_type

    @staticmethod
    def _create_team_deliverable_file(actor, team, uploaded_file):
        original_filename, file_size, content_type = DefenseService._extract_file_metadata(uploaded_file)
        return DeliverableFile.objects.create(
            team=team,
            file=uploaded_file,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            uploaded_by=actor,
        )

    @staticmethod
    def _resolve_existing_files(team, existing_file_ids):
        if not existing_file_ids:
            return []
        files = list(DeliverableFile.objects.filter(id__in=existing_file_ids, team=team))
        if len(files) != len(set(str(file_id) for file_id in existing_file_ids)):
            raise serializers.ValidationError({"existing_file_ids": "Selected files must belong to the same team."})
        return files

    @staticmethod
    def _create_attached_files(defense, files, added_by, ordering=None):
        if not files:
            raise serializers.ValidationError({"files": "Defense request must include at least one file."})
        file_map = {str(deliverable_file.id): deliverable_file for deliverable_file in files}
        if len(file_map) != len(files):
            raise serializers.ValidationError({"files": "The same file cannot be attached twice."})
        if ordering:
            normalized_ordering = [str(file_id) for file_id in ordering]
            if set(normalized_ordering) != set(file_map.keys()):
                raise serializers.ValidationError({"ordering": "Ordering must reference each attached file exactly once."})
            ordered_files = [file_map[file_id] for file_id in normalized_ordering]
        else:
            ordered_files = files
        DefenseAttachedFile.objects.bulk_create(
            [
                DefenseAttachedFile(
                    defense=defense,
                    deliverable_file=deliverable_file,
                    order=index,
                    added_by=added_by,
                )
                for index, deliverable_file in enumerate(ordered_files, start=1)
            ]
        )

    @staticmethod
    def _is_active_supervisor(team, user):
        return TeamParticipant.objects.filter(
            team=team,
            user=user,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
        ).exists()

    @staticmethod
    def _ensure_jury_user_allowed(defense, user, role):
        if role == DefenseJuryAssignment.JuryRole.PRESIDENT and DefenseService._is_active_supervisor(defense.team, user):
            raise serializers.ValidationError({"president_user_id": "A supervisor cannot be PRESIDENT of this defense."})
        if role == DefenseJuryAssignment.JuryRole.EXAMINER and DefenseService._is_active_supervisor(defense.team, user):
            raise serializers.ValidationError({"examiner_user_ids": "Supervisors must remain GUEST jury members."})

    @staticmethod
    def _rebuild_jury_assignments(defense, assigned_by, president_user, examiner_users, guest_users=None):
        guest_users = guest_users or []
        if president_user is None:
            raise serializers.ValidationError({"president_user_id": "Exactly one PRESIDENT is required."})
        if not examiner_users:
            raise serializers.ValidationError({"examiner_user_ids": "At least one EXAMINER is required."})

        DefenseService._ensure_jury_user_allowed(defense, president_user, DefenseJuryAssignment.JuryRole.PRESIDENT)
        for examiner in examiner_users:
            DefenseService._ensure_jury_user_allowed(defense, examiner, DefenseJuryAssignment.JuryRole.EXAMINER)

        supervisor_users = [participant.user for participant in DefenseService._active_supervisors(defense.team)]
        assignments = {}

        def add_assignment(user, role, field_name):
            if user.id in assignments:
                raise serializers.ValidationError({field_name: "Duplicate jury users are not allowed."})
            assignments[user.id] = (user, role)

        add_assignment(president_user, DefenseJuryAssignment.JuryRole.PRESIDENT, "president_user_id")
        for examiner in examiner_users:
            add_assignment(examiner, DefenseJuryAssignment.JuryRole.EXAMINER, "examiner_user_ids")
        for guest in guest_users:
            if DefenseService._is_active_supervisor(defense.team, guest):
                continue
            add_assignment(guest, DefenseJuryAssignment.JuryRole.GUEST, "guest_user_ids")
        for supervisor in supervisor_users:
            if supervisor.id == president_user.id or supervisor.id in {examiner.id for examiner in examiner_users}:
                raise serializers.ValidationError(
                    {"jury": "Supervisors are added automatically as GUEST and cannot be PRESIDENT or EXAMINER."}
                )
            if supervisor.id not in assignments:
                assignments[supervisor.id] = (supervisor, DefenseJuryAssignment.JuryRole.GUEST)

        defense.jury_assignments.all().delete()
        DefenseJuryAssignment.objects.bulk_create(
            [
                DefenseJuryAssignment(
                    defense=defense,
                    user=user,
                    role=role,
                    assigned_by=assigned_by,
                )
                for user, role in assignments.values()
            ]
        )

    @staticmethod
    @transaction.atomic
    def request_defense(actor, existing_file_ids=None, uploaded_files=None, ordering=None):
        actor = TeamService.lock_user(actor)
        participation = TeamService.get_active_student_participation(actor)
        team = participation.team if participation else None
        DefenseService._ensure_team_ready_for_defense_request(team)
        if participation is None or participation.role != TeamParticipant.Role.LEADER:
            raise serializers.ValidationError({"detail": "Only the active team leader can request a defense."})
        DefenseService._require_defense_window(team.academic_year)
        supervisors = DefenseService._active_supervisors(team)
        if not supervisors:
            raise serializers.ValidationError({"team": "Team must have at least one active supervisor."})
        DefenseService._ensure_no_active_defense(team)

        existing_files = DefenseService._resolve_existing_files(team, existing_file_ids or [])
        uploaded_deliverables = [
            DefenseService._create_team_deliverable_file(actor, team, uploaded_file)
            for uploaded_file in (uploaded_files or [])
        ]
        attached_files = existing_files + uploaded_deliverables
        if not attached_files:
            raise serializers.ValidationError({"files": "Defense request must include at least one file."})

        defense = Defense.objects.create(
            team=team,
            status=Defense.Status.REQUESTED,
            requested_by=actor,
            requested_at=timezone.now(),
        )
        DefenseService._create_attached_files(defense, attached_files, added_by=actor, ordering=ordering)
        DefenseSupervisorDecision.objects.bulk_create(
            [
                DefenseSupervisorDecision(
                    defense=defense,
                    supervisor=participant.user,
                    decision=DefenseSupervisorDecision.DecisionStatus.PENDING,
                )
                for participant in supervisors
            ]
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_defense_requested(defense, actor=actor)
        return defense

    @staticmethod
    @transaction.atomic
    def decide_supervisor(defense, supervisor_user, decision):
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status != Defense.Status.REQUESTED:
            raise serializers.ValidationError({"defense": "Supervisor decisions are allowed only while defense is REQUESTED."})
        supervisor_decision = DefenseSupervisorDecision.objects.select_for_update().filter(
            defense=defense,
            supervisor=supervisor_user,
        ).first()
        if supervisor_decision is None:
            raise serializers.ValidationError({"detail": "Only active supervisors can decide on this defense."})
        if supervisor_decision.decision != DefenseSupervisorDecision.DecisionStatus.PENDING:
            raise serializers.ValidationError({"decision": "This supervisor decision is no longer pending."})

        supervisor_decision.decision = decision
        supervisor_decision.decided_at = timezone.now()
        supervisor_decision.save(update_fields=["decision", "decided_at"])

        if decision == DefenseSupervisorDecision.DecisionStatus.DENIED:
            defense.status = Defense.Status.CANCELLED
            defense.save(update_fields=["status", "updated_at"])
            from apps.notifications.services import NotificationService

            NotificationService.notify_defense_supervisor_decision(
                defense,
                supervisor_user,
                accepted=False,
                actor=supervisor_user,
            )
            # Leader already got the personal notification above; this informs
            # the rest of the team that the workflow is cancelled.
            NotificationService.notify_defense_cancelled(defense, actor=supervisor_user)
            return defense

        if not defense.supervisor_decisions.filter(
            decision=DefenseSupervisorDecision.DecisionStatus.PENDING
        ).exists():
            defense.status = Defense.Status.READY_TO_SCHEDULE
            defense.save(update_fields=["status", "updated_at"])
            from apps.notifications.services import NotificationService

            NotificationService.notify_defense_supervisor_decision(
                defense,
                supervisor_user,
                accepted=True,
                actor=supervisor_user,
            )
            NotificationService.notify_defense_ready_to_schedule(defense, actor=supervisor_user)
            return defense
        from apps.notifications.services import NotificationService

        NotificationService.notify_defense_supervisor_decision(
            defense,
            supervisor_user,
            accepted=True,
            actor=supervisor_user,
        )
        return defense

    @staticmethod
    @transaction.atomic
    def schedule_defense(admin_user, defense, scheduled_at, location, president_user, examiner_users, guest_users=None):
        DefenseService._ensure_platform_admin(admin_user)
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status != Defense.Status.READY_TO_SCHEDULE:
            raise serializers.ValidationError({"defense": "Only READY_TO_SCHEDULE defenses can be scheduled."})
        DefenseService._rebuild_jury_assignments(defense, admin_user, president_user, examiner_users, guest_users=guest_users)
        defense.scheduled_at = scheduled_at
        defense.location = location or ""
        defense.scheduled_by = admin_user
        defense.status = Defense.Status.SCHEDULED
        defense.save(update_fields=["scheduled_at", "location", "scheduled_by", "status", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_defense_scheduled(defense, actor=admin_user)
        NotificationService.notify_jury_assigned(defense, actor=admin_user)
        return defense

    @staticmethod
    @transaction.atomic
    def reschedule_defense(admin_user, defense, scheduled_at=None, location=None):
        DefenseService._ensure_platform_admin(admin_user)
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status != Defense.Status.SCHEDULED:
            raise serializers.ValidationError({"defense": "Only SCHEDULED defenses can be rescheduled."})
        if scheduled_at is not None:
            defense.scheduled_at = scheduled_at
        if location is not None:
            defense.location = location
        defense.save(update_fields=["scheduled_at", "location", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_defense_scheduled(defense, actor=admin_user, rescheduled=True)
        return defense

    @staticmethod
    @transaction.atomic
    def update_jury(admin_user, defense, president_user, examiner_users, guest_users=None):
        DefenseService._ensure_platform_admin(admin_user)
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status != Defense.Status.SCHEDULED:
            raise serializers.ValidationError({"defense": "Jury can be updated only for SCHEDULED defenses."})

        # Snapshot the current jury user set BEFORE rebuild so we can diff and
        # notify the newcomers (existing jurors don't need a second ping).
        previous_user_ids = set(
            defense.jury_assignments.values_list("user_id", flat=True)
        )
        DefenseService._rebuild_jury_assignments(defense, admin_user, president_user, examiner_users, guest_users=guest_users)
        new_jurors = [
            assignment.user
            for assignment in defense.jury_assignments.select_related("user").all()
            if assignment.user_id not in previous_user_ids
        ]
        if new_jurors:
            from apps.notifications.services import NotificationService

            NotificationService.notify_defense_jury_updated(defense, new_jurors, actor=admin_user)
        return defense

    @staticmethod
    @transaction.atomic
    def update_attached_files(admin_user, defense, existing_file_ids=None, uploaded_files=None, remove_ids=None, ordering=None):
        DefenseService._ensure_platform_admin(admin_user)
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status not in {Defense.Status.READY_TO_SCHEDULE, Defense.Status.SCHEDULED}:
            raise serializers.ValidationError({"defense": "Attached files can be modified only before completion."})

        current_attachments = list(defense.attached_files.select_for_update().select_related("deliverable_file").order_by("order"))
        attachments_by_id = {str(item.id): item for item in current_attachments}
        kept_attachments = [item for item in current_attachments if str(item.id) not in {str(value) for value in (remove_ids or [])}]

        existing_files = DefenseService._resolve_existing_files(defense.team, existing_file_ids or [])
        uploaded_deliverables = [
            DefenseService._create_team_deliverable_file(admin_user, defense.team, uploaded_file)
            for uploaded_file in (uploaded_files or [])
        ]
        existing_ids = {item.deliverable_file_id for item in kept_attachments}
        new_files = [deliverable_file for deliverable_file in existing_files + uploaded_deliverables if deliverable_file.id not in existing_ids]
        resulting_files = [item.deliverable_file for item in kept_attachments] + new_files
        if not resulting_files:
            raise serializers.ValidationError({"files": "Defense must keep at least one attached file."})

        if ordering:
            normalized_ordering = [str(file_id) for file_id in ordering]
            file_map = {str(deliverable_file.id): deliverable_file for deliverable_file in resulting_files}
            if set(normalized_ordering) != set(file_map.keys()):
                raise serializers.ValidationError({"ordering": "Ordering must reference each remaining file exactly once."})
            resulting_files = [file_map[file_id] for file_id in normalized_ordering]

        for removed_id in remove_ids or []:
            attachment = attachments_by_id.get(str(removed_id))
            if attachment is not None:
                attachment.delete()

        defense.attached_files.all().delete()
        DefenseAttachedFile.objects.bulk_create(
            [
                DefenseAttachedFile(
                    defense=defense,
                    deliverable_file=deliverable_file,
                    order=index,
                    added_by=admin_user,
                )
                for index, deliverable_file in enumerate(resulting_files, start=1)
            ]
        )
        # Only fire for SCHEDULED — jurors care about file changes only after
        # they have access. Pre-schedule edits don't need to notify anyone.
        if defense.status == Defense.Status.SCHEDULED:
            from apps.notifications.services import NotificationService

            NotificationService.notify_defense_files_updated(defense, actor=admin_user)
        return defense

    @staticmethod
    def _can_upload_pv(actor, defense):
        if get_platform_levels(actor).intersection({"ADMIN", "SUPER_ADMIN"}):
            return True
        return DefenseJuryAssignment.objects.filter(
            defense=defense,
            user=actor,
            role=DefenseJuryAssignment.JuryRole.PRESIDENT,
        ).exists()

    @staticmethod
    @transaction.atomic
    def upload_pv(actor, defense, final_grade, deliberation, pv_file):
        defense = Defense.objects.select_for_update().select_related("team", "team__academic_year").get(pk=defense.pk)
        DefenseService._require_defense_window(defense.team.academic_year)
        if defense.status != Defense.Status.SCHEDULED:
            raise serializers.ValidationError({"defense": "PV can be uploaded only for SCHEDULED defenses."})
        if not DefenseService._can_upload_pv(actor, defense):
            raise serializers.ValidationError({"detail": "Only the PRESIDENT or a platform admin can upload the PV."})
        defense.final_grade = final_grade
        defense.deliberation = deliberation.strip()
        defense.pv_file = pv_file
        defense.pv_uploaded_by = actor
        defense.pv_uploaded_at = timezone.now()
        defense.status = Defense.Status.COMPLETED
        defense.save(
            update_fields=[
                "final_grade",
                "deliberation",
                "pv_file",
                "pv_uploaded_by",
                "pv_uploaded_at",
                "status",
                "updated_at",
            ]
        )
        from apps.notifications.services import NotificationService

        NotificationService.notify_pv_uploaded(defense, actor=actor)
        return defense

    @staticmethod
    def list_my_defense(user):
        team = TeamService.get_active_student_team(user)
        if team is None:
            return None
        return (
            Defense.objects.filter(team=team)
            .prefetch_related("attached_files__deliverable_file", "supervisor_decisions__supervisor", "jury_assignments__user")
            .select_related("requested_by", "scheduled_by", "pv_uploaded_by")
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def list_supervisor_requests(supervisor_user):
        return (
            Defense.objects.filter(supervisor_decisions__supervisor=supervisor_user)
            .exclude(team__academic_year__status="ARCHIVED")
            .prefetch_related("attached_files__deliverable_file", "supervisor_decisions__supervisor")
            .select_related("team", "requested_by", "scheduled_by", "pv_uploaded_by")
            .distinct()
            .order_by("-created_at")
        )

    @staticmethod
    def list_jury_defenses(user):
        return (
            Defense.objects.filter(
                jury_assignments__user=user,
                status__in=[Defense.Status.SCHEDULED, Defense.Status.COMPLETED],
            )
            .exclude(team__academic_year__status="ARCHIVED")
            .prefetch_related("attached_files__deliverable_file", "jury_assignments__user")
            .select_related("team", "requested_by", "scheduled_by", "pv_uploaded_by")
            .distinct()
            .order_by("-scheduled_at", "-created_at")
        )

    @staticmethod
    def can_access_defense_files(user, defense):
        from apps.archives.services import AcademicYearLifecycleService

        if not AcademicYearLifecycleService.can_access_archived_year(user, defense.team.academic_year):
            return False
        if get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}):
            return True
        if DefenseService._active_member_or_leader(defense.team, user):
            return True
        if DefenseService._is_active_supervisor(defense.team, user):
            return True
        if DefenseJuryAssignment.objects.filter(defense=defense, user=user).exists() and defense.status in {
            Defense.Status.SCHEDULED,
            Defense.Status.COMPLETED,
        }:
            return True
        return False
