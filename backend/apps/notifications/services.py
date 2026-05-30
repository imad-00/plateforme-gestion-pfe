from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.accounts.permissions import get_platform_levels
from apps.academics.models import AcademicYear
from apps.notifications.models import Notification, NotificationDelivery
from apps.teams.models import TeamParticipant


class NotificationService:
    @staticmethod
    def _is_platform_admin(user):
        return bool(get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}))

    @staticmethod
    def _is_active_recipient(user):
        return (
            user is not None
            and getattr(user, "account_status", None) == User.AccountStatus.ACTIVE
        )

    @staticmethod
    def _should_skip_for_archived_year(recipient, academic_year):
        return (
            academic_year is not None
            and academic_year.status == AcademicYear.Status.ARCHIVED
            and not NotificationService._is_platform_admin(recipient)
        )

    @staticmethod
    def _dedupe_recipients(recipients):
        deduped = []
        seen = set()
        for recipient in recipients or []:
            if recipient is None or recipient.pk in seen:
                continue
            seen.add(recipient.pk)
            deduped.append(recipient)
        return deduped

    @staticmethod
    def notify_user(
        recipient,
        notification_type,
        title,
        message,
        importance,
        link_url=None,
        metadata=None,
        actor=None,
        academic_year=None,
    ):
        if not NotificationService._is_active_recipient(recipient):
            return None
        if NotificationService._should_skip_for_archived_year(recipient, academic_year):
            return None

        notification = Notification.objects.create(
            recipient=recipient,
            type=notification_type,
            importance=importance,
            title=title,
            message=message,
            link_url=link_url or "",
            metadata=metadata or {},
        )
        NotificationService.maybe_enqueue_email(notification)
        return notification

    @staticmethod
    def notify_many(
        recipients,
        notification_type,
        title,
        message,
        importance,
        link_url=None,
        metadata=None,
        actor=None,
        academic_year=None,
    ):
        notifications = []
        for recipient in NotificationService._dedupe_recipients(recipients):
            notification = NotificationService.notify_user(
                recipient,
                notification_type,
                title,
                message,
                importance,
                link_url=link_url,
                metadata=metadata,
                actor=actor,
                academic_year=academic_year,
            )
            if notification is not None:
                notifications.append(notification)
        return notifications

    @staticmethod
    def maybe_enqueue_email(notification):
        if notification.importance != Notification.Importance.IMPORTANT:
            return None
        delivery, _created = NotificationDelivery.objects.get_or_create(
            notification=notification,
            channel=NotificationDelivery.Channel.EMAIL,
            defaults={"status": NotificationDelivery.Status.PENDING},
        )

        def enqueue():
            from apps.notifications.tasks import send_notification_email

            send_notification_email.delay(notification.id)

        transaction.on_commit(enqueue)
        return delivery

    @staticmethod
    def list_for_user(user):
        return Notification.objects.filter(recipient=user).order_by("-created_at", "-id")

    @staticmethod
    def unread_count(user):
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def mark_read(user, notification):
        if notification.recipient_id != user.id:
            raise PermissionDenied("You can mark only your own notifications as read.")
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    def mark_all_read(user):
        now = timezone.now()
        return Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=now,
            updated_at=now,
        )

    @staticmethod
    def get_platform_admin_recipients():
        return (
            User.objects.filter(
                account_status=User.AccountStatus.ACTIVE,
                platform_access_grants__revoked_at__isnull=True,
                platform_access_grants__access_level__in=["ADMIN", "SUPER_ADMIN"],
            )
            .distinct()
            .order_by("id")
        )

    @staticmethod
    def active_team_members(team):
        return [
            participant.user
            for participant in TeamParticipant.objects.select_related("user").filter(
                team=team,
                role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
                status=TeamParticipant.Status.ACTIVE,
            )
        ]

    @staticmethod
    def active_team_supervisors(team):
        return [
            participant.user
            for participant in TeamParticipant.objects.select_related("user").filter(
                team=team,
                role=TeamParticipant.Role.SUPERVISOR,
                status=TeamParticipant.Status.ACTIVE,
            )
        ]

    @staticmethod
    def active_team_leader(team):
        participant = (
            TeamParticipant.objects.select_related("user")
            .filter(
                team=team,
                role=TeamParticipant.Role.LEADER,
                status=TeamParticipant.Status.ACTIVE,
            )
            .first()
        )
        return participant.user if participant else None

    @staticmethod
    def notify_team_invitation_received(participation, actor=None):
        return NotificationService.notify_user(
            participation.user,
            Notification.Type.TEAM_INVITATION_RECEIVED,
            "Team invitation received",
            f"You have been invited to join team {participation.team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": participation.team_id, "participation_id": str(participation.pk)},
            actor=actor,
            academic_year=participation.team.academic_year,
        )

    @staticmethod
    def notify_team_member_joined(team, member, actor=None):
        leader = NotificationService.active_team_leader(team)
        if leader is None or leader.id == member.id:
            return []
        return NotificationService.notify_many(
            [leader],
            Notification.Type.TEAM_MEMBER_JOINED,
            "Team member joined",
            f"{member.full_name or member.matricule} joined team {team.name}.",
            Notification.Importance.NORMAL,
            metadata={"team_code": team.pk, "member_id": member.id},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_team_member_left(team, member, actor=None):
        leader = NotificationService.active_team_leader(team)
        if leader is None or leader.id == member.id:
            return []
        return NotificationService.notify_many(
            [leader],
            Notification.Type.TEAM_MEMBER_LEFT,
            "Team member left",
            f"{member.full_name or member.matricule} left team {team.name}.",
            Notification.Importance.NORMAL,
            metadata={"team_code": team.pk, "member_id": member.id},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_team_member_removed(team, member, actor=None):
        return NotificationService.notify_user(
            member,
            Notification.Type.TEAM_MEMBER_REMOVED,
            "Removed from team",
            f"You were removed from team {team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": team.pk},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_leadership_transferred(team, new_leader, old_leader=None, actor=None):
        recipients = [new_leader]
        return NotificationService.notify_many(
            recipients,
            Notification.Type.LEADERSHIP_TRANSFERRED,
            "Leadership transferred",
            f"You are now the leader of team {team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": team.pk, "old_leader_id": getattr(old_leader, "id", None)},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_team_locked(team, actor=None):
        return NotificationService.notify_many(
            NotificationService.active_team_members(team),
            Notification.Type.TEAM_LOCKED,
            "Team locked",
            f"Team {team.name} has been locked.",
            Notification.Importance.NORMAL,
            metadata={"team_code": team.pk},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_subject_event(subject, notification_type, title, message, actor=None):
        return NotificationService.notify_user(
            subject.proposed_by,
            notification_type,
            title,
            message,
            Notification.Importance.IMPORTANT,
            metadata={"subject_id": subject.id, "subject_code": subject.subject_code},
            actor=actor,
            academic_year=subject.academic_year,
        )

    @staticmethod
    def notify_assignment_result_available(team, actor=None):
        return NotificationService.notify_many(
            NotificationService.active_team_members(team),
            Notification.Type.ASSIGNMENT_RESULT_AVAILABLE,
            "Assignment result available",
            f"An assignment result is available for team {team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": team.pk},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_appeal_submitted(appeal, actor=None):
        recipients = list(NotificationService.get_platform_admin_recipients())
        if not recipients:
            recipients = [appeal.submitted_by]
        return NotificationService.notify_many(
            recipients,
            Notification.Type.APPEAL_SUBMITTED,
            "Appeal submitted",
            f"An appeal was submitted for team {appeal.team.name}.",
            Notification.Importance.NORMAL,
            metadata={"appeal_id": str(appeal.pk), "team_code": appeal.team_id},
            actor=actor,
            academic_year=appeal.team.academic_year,
        )

    @staticmethod
    def notify_appeal_decision(appeal, accepted, actor=None):
        notification_type = Notification.Type.APPEAL_ACCEPTED if accepted else Notification.Type.APPEAL_REJECTED
        title = "Appeal accepted" if accepted else "Appeal rejected"
        return NotificationService.notify_many(
            NotificationService.active_team_members(appeal.team),
            notification_type,
            title,
            f"The appeal for team {appeal.team.name} was {'accepted' if accepted else 'rejected'}.",
            Notification.Importance.IMPORTANT,
            metadata={"appeal_id": str(appeal.pk), "team_code": appeal.team_id},
            actor=actor,
            academic_year=appeal.team.academic_year,
        )

    @staticmethod
    def notify_deliverable_uploaded(deliverable_file, actor=None):
        recipients = NotificationService.active_team_supervisors(deliverable_file.team)
        leader = NotificationService.active_team_leader(deliverable_file.team)
        if leader is not None:
            recipients.append(leader)
        recipients = [recipient for recipient in recipients if actor is None or recipient.id != actor.id]
        return NotificationService.notify_many(
            recipients,
            Notification.Type.DELIVERABLE_UPLOADED,
            "Deliverable uploaded",
            f"A file was uploaded for team {deliverable_file.team.name}.",
            Notification.Importance.NORMAL,
            metadata={"file_id": str(deliverable_file.pk), "team_code": deliverable_file.team_id},
            actor=actor,
            academic_year=deliverable_file.team.academic_year,
        )

    @staticmethod
    def notify_deliverable_reviewed(deliverable_file, actor=None):
        return NotificationService.notify_many(
            NotificationService.active_team_members(deliverable_file.team),
            Notification.Type.DELIVERABLE_REVIEWED,
            "Deliverable reviewed",
            f"A file for team {deliverable_file.team.name} was reviewed.",
            Notification.Importance.IMPORTANT,
            metadata={"file_id": str(deliverable_file.pk), "review_status": deliverable_file.review_status},
            actor=actor,
            academic_year=deliverable_file.team.academic_year,
        )

    @staticmethod
    def notify_deliverable_comment_added(comment, actor=None):
        recipients = NotificationService.active_team_members(comment.deliverable_file.team)
        recipients += NotificationService.active_team_supervisors(comment.deliverable_file.team)
        recipients = [recipient for recipient in recipients if actor is None or recipient.id != actor.id]
        return NotificationService.notify_many(
            recipients,
            Notification.Type.DELIVERABLE_COMMENT_ADDED,
            "Deliverable comment added",
            f"A comment was added to a file for team {comment.deliverable_file.team.name}.",
            Notification.Importance.NORMAL,
            metadata={"file_id": str(comment.deliverable_file_id), "comment_id": str(comment.pk)},
            actor=actor,
            academic_year=comment.deliverable_file.team.academic_year,
        )

    @staticmethod
    def notify_defense_requested(defense, actor=None):
        return NotificationService.notify_many(
            NotificationService.active_team_supervisors(defense.team),
            Notification.Type.DEFENSE_REQUESTED,
            "Defense requested",
            f"Team {defense.team.name} requested a defense.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_defense_supervisor_decision(defense, supervisor, accepted, actor=None):
        leader = NotificationService.active_team_leader(defense.team)
        if leader is None:
            return []
        notification_type = (
            Notification.Type.DEFENSE_SUPERVISOR_ACCEPTED
            if accepted
            else Notification.Type.DEFENSE_SUPERVISOR_DENIED
        )
        title = "Defense request accepted" if accepted else "Defense request denied"
        return NotificationService.notify_many(
            [leader],
            notification_type,
            title,
            f"{supervisor.full_name or supervisor.matricule} {'accepted' if accepted else 'denied'} the defense request.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "supervisor_id": supervisor.id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_defense_ready_to_schedule(defense, actor=None):
        # IMPORTANT (was NORMAL) — gap-fill pass: admins should get the email
        # because the workflow stalls if no admin sees the bell.
        return NotificationService.notify_many(
            NotificationService.get_platform_admin_recipients(),
            Notification.Type.DEFENSE_READY_TO_SCHEDULE,
            "Defense ready to schedule",
            f"Team {defense.team.name} is ready to schedule.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_defense_scheduled(defense, actor=None, rescheduled=False):
        recipients = NotificationService.active_team_members(defense.team)
        recipients += NotificationService.active_team_supervisors(defense.team)
        recipients += [assignment.user for assignment in defense.jury_assignments.select_related("user").all()]
        notification_type = Notification.Type.DEFENSE_RESCHEDULED if rescheduled else Notification.Type.DEFENSE_SCHEDULED
        title = "Defense rescheduled" if rescheduled else "Defense scheduled"
        return NotificationService.notify_many(
            recipients,
            notification_type,
            title,
            f"Defense for team {defense.team.name} has been {'rescheduled' if rescheduled else 'scheduled'}.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_jury_assigned(defense, actor=None):
        return NotificationService.notify_many(
            [assignment.user for assignment in defense.jury_assignments.select_related("user").all()],
            Notification.Type.JURY_ASSIGNED,
            "Jury assignment",
            f"You have been assigned to the jury for team {defense.team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_pv_uploaded(defense, actor=None):
        return NotificationService.notify_many(
            NotificationService.active_team_members(defense.team),
            Notification.Type.PV_UPLOADED,
            "PV uploaded",
            f"The PV for team {defense.team.name} has been uploaded.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_academic_year_lifecycle(academic_year, event_type, actor=None):
        title_by_type = {
            Notification.Type.ACADEMIC_YEAR_CLOSED: "Academic year closed",
            Notification.Type.ACADEMIC_YEAR_FORCE_CLOSED: "Academic year force closed",
            Notification.Type.ACADEMIC_YEAR_REOPENED: "Academic year reopened",
            Notification.Type.ACADEMIC_YEAR_ARCHIVED: "Academic year archived",
        }
        return NotificationService.notify_many(
            NotificationService.get_platform_admin_recipients(),
            event_type,
            title_by_type[event_type],
            f"Academic year {academic_year.year} lifecycle event: {title_by_type[event_type]}.",
            Notification.Importance.IMPORTANT,
            metadata={"academic_year_id": academic_year.id, "status": academic_year.status},
            actor=actor,
            academic_year=academic_year,
        )

    # ─── 2026-05-30 gap-fill additions ───────────────────────────────────────

    @staticmethod
    def notify_team_invitation_rejected(participation, actor=None):
        """When an invitee declines, tell the leader who sent the invite."""
        leader = NotificationService.active_team_leader(participation.team)
        if leader is None:
            return []
        invitee = participation.user
        return NotificationService.notify_many(
            [leader],
            Notification.Type.TEAM_INVITATION_REJECTED,
            "Team invitation declined",
            f"{invitee.full_name or invitee.matricule} declined the invitation to team {participation.team.name}.",
            Notification.Importance.NORMAL,
            metadata={"team_code": participation.team_id, "participation_id": str(participation.pk)},
            actor=actor,
            academic_year=participation.team.academic_year,
        )

    @staticmethod
    def notify_team_dissolved(team, recipients, actor=None):
        """Admin dissolves a team — notify everyone who was on it."""
        return NotificationService.notify_many(
            recipients,
            Notification.Type.TEAM_DISSOLVED,
            "Team dissolved",
            f"Team {team.name} was dissolved by an administrator.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": team.pk},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_team_supervisor_added(team, supervisor, actor=None):
        """Admin adds a supervisor. Notify the supervisor (IMPORTANT — new
        responsibility) and the team members (NORMAL — they want to know who's
        watching their work)."""
        notifications = []
        notifications.extend(
            NotificationService.notify_many(
                [supervisor],
                Notification.Type.TEAM_SUPERVISOR_ADDED,
                "Added as supervisor",
                f"You have been added as a supervisor to team {team.name}.",
                Notification.Importance.IMPORTANT,
                metadata={"team_code": team.pk, "supervisor_id": supervisor.id},
                actor=actor,
                academic_year=team.academic_year,
            )
        )
        members = NotificationService.active_team_members(team)
        if members:
            notifications.extend(
                NotificationService.notify_many(
                    members,
                    Notification.Type.TEAM_SUPERVISOR_ADDED,
                    "New supervisor on your team",
                    f"{supervisor.full_name or supervisor.matricule} is now a supervisor of team {team.name}.",
                    Notification.Importance.NORMAL,
                    metadata={"team_code": team.pk, "supervisor_id": supervisor.id},
                    actor=actor,
                    academic_year=team.academic_year,
                )
            )
        return notifications

    @staticmethod
    def notify_team_supervisor_removed(team, supervisor, actor=None):
        """Admin removes a supervisor from a team."""
        return NotificationService.notify_many(
            [supervisor],
            Notification.Type.TEAM_SUPERVISOR_REMOVED,
            "Removed as supervisor",
            f"You were removed as a supervisor of team {team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"team_code": team.pk, "supervisor_id": supervisor.id},
            actor=actor,
            academic_year=team.academic_year,
        )

    @staticmethod
    def notify_subject_pending_moderation(subject, actor=None):
        """A teacher submitted a subject — admins should know there's pending
        moderation work."""
        return NotificationService.notify_many(
            NotificationService.get_platform_admin_recipients(),
            Notification.Type.SUBJECT_PENDING_MODERATION,
            "Subject pending moderation",
            f"A new subject is awaiting moderation: {subject.title}.",
            Notification.Importance.NORMAL,
            metadata={"subject_id": subject.id, "subject_code": subject.subject_code},
            actor=actor,
            academic_year=subject.academic_year,
        )

    @staticmethod
    def notify_subject_archived(subject, actor=None):
        """Admin archives a subject — confirm to the proposer."""
        return NotificationService.notify_user(
            subject.proposed_by,
            Notification.Type.SUBJECT_ARCHIVED,
            "Subject archived",
            f"Your subject \"{subject.title}\" has been archived by an administrator.",
            Notification.Importance.NORMAL,
            metadata={"subject_id": subject.id, "subject_code": subject.subject_code},
            actor=actor,
            academic_year=subject.academic_year,
        )

    @staticmethod
    def notify_subject_assigned_to_team(subject, team, actor=None):
        """A subject was reserved for a team — tell the proposer they're now
        an auto-supervisor."""
        return NotificationService.notify_user(
            subject.proposed_by,
            Notification.Type.SUBJECT_ASSIGNED_TO_TEAM,
            "Your subject was assigned",
            f"Your subject \"{subject.title}\" has been assigned to team {team.name}. You are now a supervisor of that team.",
            Notification.Importance.IMPORTANT,
            metadata={"subject_id": subject.id, "team_code": team.pk},
            actor=actor,
            academic_year=subject.academic_year,
        )

    @staticmethod
    def notify_defense_cancelled(defense, actor=None):
        """A supervisor denied the defense — workflow cancelled. The leader
        already got DEFENSE_SUPERVISOR_DENIED individually; this informs the
        rest of the active team."""
        leader = NotificationService.active_team_leader(defense.team)
        leader_id = leader.id if leader else None
        recipients = [
            user for user in NotificationService.active_team_members(defense.team)
            if user.id != leader_id
        ]
        if not recipients:
            return []
        return NotificationService.notify_many(
            recipients,
            Notification.Type.DEFENSE_CANCELLED,
            "Defense cancelled",
            f"The defense for team {defense.team.name} was cancelled because a supervisor declined the request.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_defense_jury_updated(defense, newly_assigned_users, actor=None):
        """Admin updates the jury (post-scheduling) — notify the new jurors."""
        if not newly_assigned_users:
            return []
        return NotificationService.notify_many(
            newly_assigned_users,
            Notification.Type.DEFENSE_JURY_UPDATED,
            "Jury updated",
            f"You have been added to the jury for team {defense.team.name}.",
            Notification.Importance.IMPORTANT,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_defense_files_updated(defense, actor=None):
        """Admin changed the attached files — jury should re-fetch."""
        jury_users = [
            assignment.user for assignment in defense.jury_assignments.select_related("user").all()
        ]
        if not jury_users:
            return []
        return NotificationService.notify_many(
            jury_users,
            Notification.Type.DEFENSE_FILES_UPDATED,
            "Defense files updated",
            f"The attached files for team {defense.team.name}'s defense were updated.",
            Notification.Importance.NORMAL,
            metadata={"defense_id": str(defense.pk), "team_code": defense.team_id},
            actor=actor,
            academic_year=defense.team.academic_year,
        )

    @staticmethod
    def notify_academic_year_opened(academic_year, actor=None):
        """A new academic year was created as ACTIVE — admins should know the
        campaign is starting."""
        return NotificationService.notify_many(
            NotificationService.get_platform_admin_recipients(),
            Notification.Type.ACADEMIC_YEAR_OPENED,
            "Academic year opened",
            f"A new academic year has been opened: {academic_year.year}.",
            Notification.Importance.IMPORTANT,
            metadata={"academic_year_id": academic_year.id},
            actor=actor,
            academic_year=academic_year,
        )

    # ─── Phase-audience map ─────────────────────────────────────────────────
    # Per-phase recipient resolution. Used by all three phase notification
    # methods so a single dict drives "who cares about this phase". Skipping
    # ARCHIVE here — admin-only and already covered by year lifecycle events.
    _PHASE_AUDIENCE_ROLES = {
        "CAMPAIGN_SETUP": ("ADMIN",),
        "SUBJECT_MANAGEMENT": ("TEACHER", "ADMIN"),
        "TEAM_FORMATION": ("STUDENT",),
        "WISHLIST_1": ("STUDENT",),
        "WISHLIST_2": ("STUDENT",),
        "ASSIGNMENT_REVIEW_1": ("ADMIN",),
        "ASSIGNMENT_REVIEW_2": ("ADMIN",),
        "RESULTS_AND_APPEALS": ("STUDENT", "ADMIN"),
        "WORK_AND_SUPERVISION": ("STUDENT", "SUPERVISOR"),
        "DEFENSE_WINDOW": ("STUDENT", "SUPERVISOR", "ADMIN"),
    }

    @staticmethod
    def _resolve_phase_audience(phase):
        """Walk the academic year for the right recipient set per phase."""
        from apps.accounts.models import User
        from apps.teams.models import TeamParticipant

        roles = NotificationService._PHASE_AUDIENCE_ROLES.get(phase.phase_type, ())
        recipients = []
        if "ADMIN" in roles:
            recipients.extend(NotificationService.get_platform_admin_recipients())
        if "STUDENT" in roles:
            recipients.extend(
                User.objects.filter(
                    business_identity=User.BusinessIdentity.STUDENT,
                    student_profile__academic_year=phase.academic_year,
                    account_status=User.AccountStatus.ACTIVE,
                ).distinct()
            )
        if "TEACHER" in roles:
            recipients.extend(
                User.objects.filter(
                    business_identity=User.BusinessIdentity.TEACHER,
                    account_status=User.AccountStatus.ACTIVE,
                ).distinct()
            )
        if "SUPERVISOR" in roles:
            recipients.extend(
                User.objects.filter(
                    team_participations__role=TeamParticipant.Role.SUPERVISOR,
                    team_participations__status=TeamParticipant.Status.ACTIVE,
                    team_participations__team__academic_year=phase.academic_year,
                    account_status=User.AccountStatus.ACTIVE,
                ).distinct()
            )
        return recipients

    @staticmethod
    def _phase_label(phase):
        return dict(
            getattr(phase.__class__, "PhaseType").choices
        ).get(phase.phase_type, phase.phase_type)

    @staticmethod
    def notify_phase_opened(phase, actor=None):
        recipients = NotificationService._resolve_phase_audience(phase)
        if not recipients:
            return []
        label = NotificationService._phase_label(phase)
        return NotificationService.notify_many(
            recipients,
            Notification.Type.CAMPAIGN_PHASE_OPENED,
            f"Phase opened: {label}",
            f"The '{label}' phase is now open. Related actions are unblocked.",
            Notification.Importance.NORMAL,
            metadata={"phase_id": phase.id, "phase_type": phase.phase_type, "academic_year_id": phase.academic_year_id},
            actor=actor,
            academic_year=phase.academic_year,
        )

    @staticmethod
    def notify_phase_closed(phase, actor=None):
        recipients = NotificationService._resolve_phase_audience(phase)
        if not recipients:
            return []
        label = NotificationService._phase_label(phase)
        return NotificationService.notify_many(
            recipients,
            Notification.Type.CAMPAIGN_PHASE_CLOSED,
            f"Phase closed: {label}",
            f"The '{label}' phase has closed. Related actions are no longer available.",
            Notification.Importance.NORMAL,
            metadata={"phase_id": phase.id, "phase_type": phase.phase_type, "academic_year_id": phase.academic_year_id},
            actor=actor,
            academic_year=phase.academic_year,
        )

    @staticmethod
    def notify_phase_closing_soon(phase):
        """One-shot reminder fired by the Celery beat task. No actor — system."""
        recipients = NotificationService._resolve_phase_audience(phase)
        if not recipients:
            return []
        label = NotificationService._phase_label(phase)
        return NotificationService.notify_many(
            recipients,
            Notification.Type.CAMPAIGN_PHASE_CLOSING_SOON,
            f"Phase closing soon: {label}",
            f"The '{label}' phase will close at {phase.end_at:%d %b %Y %H:%M}. Finish related actions before then.",
            Notification.Importance.IMPORTANT,
            metadata={"phase_id": phase.id, "phase_type": phase.phase_type, "end_at": phase.end_at.isoformat()},
            actor=None,
            academic_year=phase.academic_year,
        )

    @staticmethod
    def notify_platform_grant_received(grant, actor=None):
        """Super-admin granted ADMIN/SUPER_ADMIN to a user."""
        return NotificationService.notify_user(
            grant.user,
            Notification.Type.PLATFORM_GRANT_RECEIVED,
            "Platform access granted",
            f"You have been granted {grant.access_level} access to the platform.",
            Notification.Importance.IMPORTANT,
            metadata={"grant_id": grant.id, "access_level": grant.access_level},
            actor=actor,
        )

    @staticmethod
    def notify_platform_grant_revoked(grant, actor=None):
        """Super-admin revoked a platform grant."""
        return NotificationService.notify_user(
            grant.user,
            Notification.Type.PLATFORM_GRANT_REVOKED,
            "Platform access revoked",
            f"Your {grant.access_level} access to the platform has been revoked.",
            Notification.Importance.IMPORTANT,
            metadata={"grant_id": grant.id, "access_level": grant.access_level},
            actor=actor,
        )

    @staticmethod
    def notify_password_changed(user):
        """Self-notification after a successful password change. Security
        confirmation so the user can react quickly if it wasn't them."""
        return NotificationService.notify_user(
            user,
            Notification.Type.PASSWORD_CHANGED,
            "Password changed",
            "Your platform password was changed. If you didn't do this, contact an administrator immediately.",
            Notification.Importance.IMPORTANT,
            metadata={},
            actor=user,
        )
