from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.accounts.permissions import get_platform_levels
from apps.academics.models import AcademicYear
from apps.archives.models import AcademicYearLifecycleEvent
from apps.assignments.models import Appeal
from apps.campaigns.models import CampaignPhase
from apps.defenses.models import Defense
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject


class AcademicYearLifecycleService:
    @staticmethod
    def is_platform_admin(user):
        return bool(get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}))

    @staticmethod
    def is_super_admin(user):
        return "SUPER_ADMIN" in get_platform_levels(user)

    @staticmethod
    def _require_super_admin(user):
        if not AcademicYearLifecycleService.is_super_admin(user):
            raise PermissionDenied("SUPER_ADMIN platform access is required.")

    @staticmethod
    def _require_confirm_and_reason(reason, confirm):
        if confirm is not True:
            raise serializers.ValidationError({"confirm": "This lifecycle action requires confirm=true."})
        if not (reason or "").strip():
            raise serializers.ValidationError({"reason": "A human reason is required."})

    @staticmethod
    def assert_academic_year_writable(academic_year):
        if academic_year is None:
            raise serializers.ValidationError({"academic_year": "No academic year is configured."})
        if academic_year.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError(
                {"academic_year": "This academic year is closed or archived and cannot be modified."}
            )

    @staticmethod
    def assert_archived_access_allowed(user, academic_year):
        if academic_year is not None and academic_year.status == AcademicYear.Status.ARCHIVED:
            if not AcademicYearLifecycleService.is_platform_admin(user):
                raise PermissionDenied("Archived academic-year data is available only to platform admins.")

    @staticmethod
    def can_access_archived_year(user, academic_year):
        if academic_year is None or academic_year.status != AcademicYear.Status.ARCHIVED:
            return True
        return AcademicYearLifecycleService.is_platform_admin(user)

    @staticmethod
    def _serializable_ids(queryset, field="pk"):
        return [str(value) for value in queryset.values_list(field, flat=True)]

    @staticmethod
    def _students_linked_to_year(academic_year):
        return User.objects.filter(
            business_identity=User.BusinessIdentity.STUDENT,
            student_profile__academic_year=academic_year,
        ).distinct()

    @staticmethod
    def _external_supervisors_linked_to_year(academic_year):
        return User.objects.filter(
            business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
            team_participations__role=TeamParticipant.Role.SUPERVISOR,
            team_participations__team__academic_year=academic_year,
        ).distinct()

    @staticmethod
    def _archive_suspend_candidates(academic_year):
        students = AcademicYearLifecycleService._students_linked_to_year(academic_year).exclude(
            account_status=User.AccountStatus.ARCHIVED
        )
        external_supervisors = AcademicYearLifecycleService._external_supervisors_linked_to_year(academic_year).exclude(
            account_status=User.AccountStatus.ARCHIVED
        )
        external_supervisors = external_supervisors.exclude(
            team_participations__role=TeamParticipant.Role.SUPERVISOR,
            team_participations__status=TeamParticipant.Status.ACTIVE,
            team_participations__team__academic_year__status=AcademicYear.Status.ACTIVE,
        )
        return students.distinct(), external_supervisors.distinct()

    @staticmethod
    def check_closure_readiness(academic_year):
        teams = Team.objects.filter(academic_year=academic_year)
        defenses = Defense.objects.filter(team__academic_year=academic_year)
        appeals = Appeal.objects.filter(team__academic_year=academic_year)
        subjects = Subject.objects.filter(academic_year=academic_year)
        now = timezone.now()

        forming = teams.filter(status=Team.Status.FORMING)
        locked = teams.filter(status=Team.Status.LOCKED)
        dissolved = teams.filter(status=Team.Status.DISSOLVED)
        validated_without_completed_defense = teams.filter(status=Team.Status.VALIDATED).exclude(
            defenses__status=Defense.Status.COMPLETED
        )
        deliverables_without_completed_defense = (
            DeliverableFile.objects.filter(team__academic_year=academic_year)
            .exclude(team__defenses__status=Defense.Status.COMPLETED)
            .distinct()
        )
        unresolved_defenses = defenses.filter(
            status__in=[
                Defense.Status.REQUESTED,
                Defense.Status.READY_TO_SCHEDULE,
                Defense.Status.SCHEDULED,
            ]
        )
        pending_appeals = appeals.filter(status=Appeal.Status.PENDING)
        unassigned_subjects = subjects.filter(
            status__in=[Subject.Status.DRAFT, Subject.Status.SUBMITTED, Subject.Status.APPROVED]
        )
        open_phases = CampaignPhase.objects.filter(academic_year=academic_year, is_archived=False).filter(
            Q(end_at__isnull=True) | Q(end_at__gt=now)
        )
        students = AcademicYearLifecycleService._students_linked_to_year(academic_year)
        external_supervisors = AcademicYearLifecycleService._external_supervisors_linked_to_year(academic_year)
        suspend_students, suspend_externals = AcademicYearLifecycleService._archive_suspend_candidates(academic_year)

        blocking_issues = []
        if validated_without_completed_defense.exists():
            blocking_issues.append(
                {
                    "code": "VALIDATED_WITHOUT_COMPLETED_DEFENSE",
                    "message": "Validated teams without completed defense block normal closure.",
                    "team_codes": AcademicYearLifecycleService._serializable_ids(validated_without_completed_defense),
                }
            )
        for status_value, code in [
            (Defense.Status.REQUESTED, "DEFENSE_REQUESTED"),
            (Defense.Status.READY_TO_SCHEDULE, "DEFENSE_READY_TO_SCHEDULE"),
            (Defense.Status.SCHEDULED, "DEFENSE_SCHEDULED"),
        ]:
            queryset = defenses.filter(status=status_value)
            if queryset.exists():
                blocking_issues.append(
                    {
                        "code": code,
                        "message": f"Defenses in {status_value} state block normal closure.",
                        "defense_ids": AcademicYearLifecycleService._serializable_ids(queryset),
                    }
                )
        if pending_appeals.exists():
            blocking_issues.append(
                {
                    "code": "PENDING_APPEALS",
                    "message": "Pending appeals block normal closure.",
                    "appeal_ids": AcademicYearLifecycleService._serializable_ids(pending_appeals, "appeal_id"),
                }
            )

        warnings = []
        if forming.exists():
            warnings.append({"code": "FORMING_TEAMS", "team_codes": AcademicYearLifecycleService._serializable_ids(forming)})
        if locked.exists():
            warnings.append({"code": "LOCKED_TEAMS", "team_codes": AcademicYearLifecycleService._serializable_ids(locked)})
        if dissolved.exists():
            warnings.append({"code": "DISSOLVED_TEAMS", "team_codes": AcademicYearLifecycleService._serializable_ids(dissolved)})
        if deliverables_without_completed_defense.exists():
            warnings.append(
                {
                    "code": "DELIVERABLES_WITHOUT_COMPLETED_DEFENSE",
                    "file_ids": AcademicYearLifecycleService._serializable_ids(deliverables_without_completed_defense),
                }
            )
        if unassigned_subjects.exists():
            warnings.append({"code": "UNASSIGNED_SUBJECTS", "subject_ids": AcademicYearLifecycleService._serializable_ids(unassigned_subjects)})
        if open_phases.exists():
            warnings.append({"code": "OPEN_PHASES", "phase_ids": AcademicYearLifecycleService._serializable_ids(open_phases)})

        defense_counts = dict(defenses.values("status").annotate(count=Count("id")).values_list("status", "count"))
        team_counts = dict(teams.values("status").annotate(count=Count("team_code")).values_list("status", "count"))
        subject_counts = dict(subjects.values("status").annotate(count=Count("id")).values_list("status", "count"))

        return {
            "academic_year": {"id": academic_year.id, "year": academic_year.year, "status": academic_year.status},
            "can_close_normally": not blocking_issues,
            "can_force_close": academic_year.status == AcademicYear.Status.ACTIVE,
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "summary": {
                "teams_by_status": team_counts,
                "defenses_by_status": defense_counts,
                "subjects_by_status": subject_counts,
                "appeals_pending": pending_appeals.count(),
                "open_phases": open_phases.count(),
            },
            "affected_entities": {
                "forming_team_codes": AcademicYearLifecycleService._serializable_ids(forming),
                "locked_team_codes": AcademicYearLifecycleService._serializable_ids(locked),
                "validated_without_completed_defense_team_codes": AcademicYearLifecycleService._serializable_ids(
                    validated_without_completed_defense
                ),
                "students_linked": AcademicYearLifecycleService._serializable_ids(students, "id"),
                "external_supervisors_linked": AcademicYearLifecycleService._serializable_ids(external_supervisors, "id"),
                "students_that_would_be_suspended_on_archive": AcademicYearLifecycleService._serializable_ids(
                    suspend_students, "id"
                ),
                "external_supervisors_that_would_be_suspended_on_archive": AcademicYearLifecycleService._serializable_ids(
                    suspend_externals, "id"
                ),
            },
        }

    @staticmethod
    def _freeze_open_phases(academic_year, now):
        changed = []
        phases = CampaignPhase.objects.select_for_update().filter(academic_year=academic_year, is_archived=False).filter(
            Q(end_at__isnull=True) | Q(end_at__gt=now)
        )
        for phase in phases:
            changed.append({"id": phase.id, "phase_type": phase.phase_type, "previous_end_at": str(phase.end_at)})
            phase.end_at = now
            phase.save(update_fields=["end_at", "updated_at"])
        return changed

    @staticmethod
    def _dissolve_abandoned_teams(academic_year, now):
        changed = []
        teams = Team.objects.select_for_update().filter(
            academic_year=academic_year,
            status__in=[Team.Status.FORMING, Team.Status.LOCKED],
        )
        for team in teams:
            team.status = Team.Status.DISSOLVED
            team.dissolved_at = now
            team.save(update_fields=["status", "dissolved_at", "updated_at"])
            TeamParticipant.objects.filter(
                team=team,
                status__in=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.PENDING],
            ).update(status=TeamParticipant.Status.ENDED, ended_at=now, updated_at=now)
            changed.append(team.pk)
        TeamParticipant.objects.filter(
            team__academic_year=academic_year,
            team__status=Team.Status.DISSOLVED,
            status__in=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.PENDING],
        ).update(status=TeamParticipant.Status.ENDED, ended_at=now, updated_at=now)
        return changed

    @staticmethod
    @transaction.atomic
    def close_year(actor, academic_year, reason, force=False, confirm=False):
        AcademicYearLifecycleService._require_super_admin(actor)
        AcademicYearLifecycleService._require_confirm_and_reason(reason, confirm)
        academic_year = AcademicYear.objects.select_for_update().get(pk=academic_year.pk)
        if academic_year.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError({"academic_year": "Only ACTIVE academic years can be closed."})
        readiness = AcademicYearLifecycleService.check_closure_readiness(academic_year)
        if not force and readiness["blocking_issues"]:
            raise serializers.ValidationError(
                {"readiness": "Normal closure is blocked by unresolved work.", "report": readiness}
            )
        now = timezone.now()
        dissolved_teams = AcademicYearLifecycleService._dissolve_abandoned_teams(academic_year, now)
        phase_changes = AcademicYearLifecycleService._freeze_open_phases(academic_year, now)
        academic_year.status = AcademicYear.Status.CLOSED
        academic_year.save(update_fields=["status", "updated_at"])
        event = AcademicYearLifecycleEvent.objects.create(
            academic_year=academic_year,
            event_type=AcademicYearLifecycleEvent.EventType.FORCE_CLOSED
            if force
            else AcademicYearLifecycleEvent.EventType.CLOSED,
            performed_by=actor,
            reason=reason.strip(),
            metadata={
                "readiness": readiness,
                "dissolved_abandoned_team_codes": dissolved_teams,
                "phase_changes": phase_changes,
                "force": bool(force),
            },
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_academic_year_lifecycle(
            academic_year,
            Notification.Type.ACADEMIC_YEAR_FORCE_CLOSED if force else Notification.Type.ACADEMIC_YEAR_CLOSED,
            actor=actor,
        )
        from apps.audit.models import AdminActionLog
        from apps.audit.services import AdminActionLogService

        AdminActionLogService.log(
            actor,
            AdminActionLog.ActionType.ACADEMIC_YEAR_FORCE_CLOSED
            if force
            else AdminActionLog.ActionType.ACADEMIC_YEAR_CLOSED,
            target=academic_year,
            metadata={"event_id": event.id, "force": bool(force), "reason": reason.strip()},
        )
        return academic_year, event, readiness

    @staticmethod
    @transaction.atomic
    def reopen_year(actor, academic_year, reason, confirm=False):
        AcademicYearLifecycleService._require_super_admin(actor)
        AcademicYearLifecycleService._require_confirm_and_reason(reason, confirm)
        academic_year = AcademicYear.objects.select_for_update().get(pk=academic_year.pk)
        if academic_year.status == AcademicYear.Status.ARCHIVED:
            raise serializers.ValidationError({"academic_year": "ARCHIVED academic years cannot be reopened."})
        if academic_year.status != AcademicYear.Status.CLOSED:
            raise serializers.ValidationError({"academic_year": "Only CLOSED academic years can be reopened."})
        if AcademicYear.objects.select_for_update().filter(status=AcademicYear.Status.ACTIVE).exclude(pk=academic_year.pk).exists():
            raise serializers.ValidationError({"academic_year": "Another academic year is already ACTIVE."})
        academic_year.status = AcademicYear.Status.ACTIVE
        academic_year.save(update_fields=["status", "updated_at"])
        event = AcademicYearLifecycleEvent.objects.create(
            academic_year=academic_year,
            event_type=AcademicYearLifecycleEvent.EventType.REOPENED,
            performed_by=actor,
            reason=reason.strip(),
            metadata={"phase_reopening": "No phases were reopened automatically."},
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_academic_year_lifecycle(
            academic_year,
            Notification.Type.ACADEMIC_YEAR_REOPENED,
            actor=actor,
        )
        from apps.audit.models import AdminActionLog
        from apps.audit.services import AdminActionLogService

        AdminActionLogService.log(
            actor,
            AdminActionLog.ActionType.ACADEMIC_YEAR_REOPENED,
            target=academic_year,
            metadata={"event_id": event.id, "reason": reason.strip()},
        )
        return academic_year, event

    @staticmethod
    @transaction.atomic
    def archive_year(actor, academic_year, reason, confirm=False):
        AcademicYearLifecycleService._require_super_admin(actor)
        AcademicYearLifecycleService._require_confirm_and_reason(reason, confirm)
        academic_year = AcademicYear.objects.select_for_update().get(pk=academic_year.pk)
        if academic_year.status == AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError({"academic_year": "Cannot archive an ACTIVE academic year. Close it first."})
        if academic_year.status == AcademicYear.Status.ARCHIVED:
            raise serializers.ValidationError({"academic_year": "This academic year is already ARCHIVED."})
        if academic_year.status != AcademicYear.Status.CLOSED:
            raise serializers.ValidationError({"academic_year": "Only CLOSED academic years can be archived."})

        suspend_students, suspend_externals = AcademicYearLifecycleService._archive_suspend_candidates(academic_year)
        student_ids = list(suspend_students.filter(account_status=User.AccountStatus.ACTIVE).values_list("id", flat=True))
        external_ids = list(suspend_externals.filter(account_status=User.AccountStatus.ACTIVE).values_list("id", flat=True))
        User.objects.filter(id__in=student_ids + external_ids, account_status=User.AccountStatus.ACTIVE).update(
            account_status=User.AccountStatus.SUSPENDED,
            updated_at=timezone.now(),
        )
        academic_year.status = AcademicYear.Status.ARCHIVED
        academic_year.save(update_fields=["status", "updated_at"])
        event = AcademicYearLifecycleEvent.objects.create(
            academic_year=academic_year,
            event_type=AcademicYearLifecycleEvent.EventType.ARCHIVED,
            performed_by=actor,
            reason=reason.strip(),
            metadata={
                "suspended_student_user_ids": student_ids,
                "suspended_external_supervisor_user_ids": external_ids,
                "child_statuses_changed": False,
            },
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_academic_year_lifecycle(
            academic_year,
            Notification.Type.ACADEMIC_YEAR_ARCHIVED,
            actor=actor,
        )
        from apps.audit.models import AdminActionLog
        from apps.audit.services import AdminActionLogService

        AdminActionLogService.log(
            actor,
            AdminActionLog.ActionType.ACADEMIC_YEAR_ARCHIVED,
            target=academic_year,
            metadata={
                "event_id": event.id,
                "reason": reason.strip(),
                "suspended_student_count": len(student_ids),
                "suspended_external_supervisor_count": len(external_ids),
            },
        )
        return academic_year, event

    @staticmethod
    @transaction.atomic
    def close_and_archive_year(actor, academic_year, reason, force=False, confirm=False):
        academic_year = AcademicYear.objects.select_for_update().get(pk=academic_year.pk)
        close_event = None
        readiness = None
        if academic_year.status == AcademicYear.Status.ACTIVE:
            academic_year, close_event, readiness = AcademicYearLifecycleService.close_year(
                actor,
                academic_year,
                reason=reason,
                force=force,
                confirm=confirm,
            )
        academic_year, archive_event = AcademicYearLifecycleService.archive_year(
            actor,
            academic_year,
            reason=reason,
            confirm=confirm,
        )
        return academic_year, close_event, archive_event, readiness
