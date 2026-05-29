from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PlatformAccessGrant, User
from apps.academics.models import AcademicYear
from apps.archives.services import AcademicYearLifecycleService
from apps.assignments.services import AssignmentService
from apps.assignments.services import AppealService
from apps.campaigns.models import CampaignPhase
from apps.defenses.models import Defense, DefenseJuryAssignment
from apps.defenses.services import DefenseService
from apps.deliverables.models import DeliverableFile
from apps.deliverables.services import DeliverableFileService
from apps.notifications.models import Notification, NotificationDelivery
from apps.notifications.services import NotificationService
from apps.notifications.tasks import send_notification_email
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import InvitationService, ParticipationService, TeamService
from apps.topics.models import Subject
from apps.topics.serializers import SubjectWorkflowService


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def mute_email_enqueue(monkeypatch):
    monkeypatch.setattr(send_notification_email, "delay", lambda notification_id: None)


def make_upload(name="notice.txt", content=b"hello", content_type="text/plain"):
    return SimpleUploadedFile(name=name, content=content, content_type=content_type)


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def open_phase(year, phase_type, display_order=1):
    now = timezone.now()
    return CampaignPhase.objects.create(
        academic_year=year,
        phase_type=phase_type,
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=1),
        display_order=display_order,
    )


def set_student_year(student, year):
    student.student_profile.academic_year = year
    student.student_profile.save(update_fields=["academic_year", "updated_at"])


def create_student(user_factory, matricule, email, year, first_name="Student", last_name="One"):
    student = user_factory(
        matricule=matricule,
        email=email,
        business_identity=User.BusinessIdentity.STUDENT,
        first_name=first_name,
        last_name=last_name,
    )
    set_student_year(student, year)
    return student


def create_teacher(user_factory, matricule, email, first_name="Teacher", last_name="One"):
    return user_factory(
        matricule=matricule,
        email=email,
        business_identity=User.BusinessIdentity.TEACHER,
        first_name=first_name,
        last_name=last_name,
    )


def subject_for_team(team, teacher, year, status=Subject.Status.ASSIGNED, code="N-SUB"):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Notification subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=status,
        proposed_by=teacher,
        academic_year=year,
        assigned_to_team=team if status == Subject.Status.ASSIGNED else None,
    )


def build_validated_team(year, leader, teacher, code="N-TEAM", member=None, supervisor=None):
    team = Team.objects.create(
        team_code=code,
        academic_year=year,
        name=f"Team {code}",
        status=Team.Status.VALIDATED,
        selection_round=Team.SelectionRound.FIRST,
    )
    TeamParticipant.objects.create(
        team=team,
        user=leader,
        role=TeamParticipant.Role.LEADER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    if member is not None:
        TeamParticipant.objects.create(
            team=team,
            user=member,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.ACTIVE,
            joined_at=timezone.now(),
        )
    TeamParticipant.objects.create(
        team=team,
        user=supervisor or teacher,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    subject_for_team(team, teacher, year, code=f"{code}-SUB")
    return team


def create_deliverable(team, uploader):
    return DeliverableFile.objects.create(
        team=team,
        file=make_upload(),
        original_filename="notice.txt",
        file_size=5,
        content_type="text/plain",
        uploaded_by=uploader,
    )


@pytest.fixture
def year(db):
    return create_year()


@pytest.fixture
def student_two(user_factory, year):
    return create_student(user_factory, "N-STU-002", "n-stu-002@example.com", year, "Student", "Two")


@pytest.fixture
def teacher_two(user_factory):
    return create_teacher(user_factory, "N-TEA-002", "n-tea-002@example.com", "Teacher", "Two")


@pytest.mark.django_db
def test_notification_model_creates_in_app_notification(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)

    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "Team locked",
        "Your team was locked.",
        Notification.Importance.NORMAL,
    )

    assert notification is not None
    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.TEAM_LOCKED).exists()


@pytest.mark.django_db
def test_normal_notification_does_not_create_email_delivery(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)

    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "Normal",
        "In-app only.",
        Notification.Importance.NORMAL,
    )

    assert notification.deliveries.count() == 0


@pytest.mark.django_db
def test_important_notification_creates_email_delivery(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)

    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_INVITATION_RECEIVED,
        "Important",
        "Email too.",
        Notification.Importance.IMPORTANT,
    )

    delivery = notification.deliveries.get(channel=NotificationDelivery.Channel.EMAIL)
    assert delivery.status == NotificationDelivery.Status.PENDING


@pytest.mark.django_db
def test_email_task_marks_delivery_sent(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)
    sent = []
    monkeypatch.setattr("apps.notifications.tasks.send_mail", lambda **kwargs: sent.append(kwargs))
    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_INVITATION_RECEIVED,
        "Important",
        "Email body.",
        Notification.Importance.IMPORTANT,
    )

    send_notification_email(notification.id)

    delivery = notification.deliveries.get()
    assert delivery.status == NotificationDelivery.Status.SENT
    assert delivery.sent_at is not None
    assert sent


@pytest.mark.django_db
def test_email_task_marks_skipped_when_recipient_has_no_email(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)
    User.objects.filter(pk=student_user.pk).update(email="")
    student_user.refresh_from_db()
    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_INVITATION_RECEIVED,
        "Important",
        "Email body.",
        Notification.Importance.IMPORTANT,
    )

    send_notification_email(notification.id)

    assert notification.deliveries.get().status == NotificationDelivery.Status.SKIPPED


@pytest.mark.django_db
def test_email_task_marks_failed_on_send_exception(student_user, monkeypatch):
    mute_email_enqueue(monkeypatch)

    def explode(**kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("apps.notifications.tasks.send_mail", explode)
    notification = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_INVITATION_RECEIVED,
        "Important",
        "Email body.",
        Notification.Importance.IMPORTANT,
    )

    send_notification_email(notification.id)

    delivery = notification.deliveries.get()
    assert delivery.status == NotificationDelivery.Status.FAILED
    assert "smtp down" in delivery.error_message


@pytest.mark.django_db
def test_notification_api_lists_current_user_only(student_user, student_two, monkeypatch):
    mute_email_enqueue(monkeypatch)
    own = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "Mine",
        "My notification.",
        Notification.Importance.NORMAL,
    )
    NotificationService.notify_user(
        student_two,
        Notification.Type.TEAM_LOCKED,
        "Other",
        "Other notification.",
        Notification.Importance.NORMAL,
    )

    response = auth_client(student_user).get("/api/notifications/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]


@pytest.mark.django_db
def test_unread_count_mark_read_and_read_all(student_user, student_two, monkeypatch):
    mute_email_enqueue(monkeypatch)
    first = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "First",
        "Unread.",
        Notification.Importance.NORMAL,
    )
    NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "Second",
        "Unread.",
        Notification.Importance.NORMAL,
    )
    foreign = NotificationService.notify_user(
        student_two,
        Notification.Type.TEAM_LOCKED,
        "Foreign",
        "Unread.",
        Notification.Importance.NORMAL,
    )
    client = auth_client(student_user)

    assert client.get("/api/notifications/unread-count/").json()["unread_count"] == 2
    assert client.post(f"/api/notifications/{foreign.id}/read/").status_code == 403
    assert client.post(f"/api/notifications/{first.id}/read/").status_code == 200
    assert client.get("/api/notifications/unread-count/").json()["unread_count"] == 1
    assert client.post("/api/notifications/read-all/").status_code == 200
    assert client.get("/api/notifications/unread-count/").json()["unread_count"] == 0


@pytest.mark.django_db
def test_team_invitation_received_creates_important_notification_for_invited_student(
    student_user,
    student_two,
    year,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    team = TeamService.create_solo_team_for_student(student_user, year)

    InvitationService.invite_student(team, student_two, student_user)

    notification = Notification.objects.get(recipient=student_two, type=Notification.Type.TEAM_INVITATION_RECEIVED)
    assert notification.importance == Notification.Importance.IMPORTANT


@pytest.mark.django_db
def test_team_member_joined_and_left_notify_leader_normal(student_user, student_two, year, monkeypatch):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    team = TeamService.create_solo_team_for_student(student_user, year)
    invitation = InvitationService.invite_student(team, student_two, student_user)

    InvitationService.accept_invitation(invitation, student_two)
    ParticipationService.leave_team(student_two)

    joined = Notification.objects.get(recipient=student_user, type=Notification.Type.TEAM_MEMBER_JOINED)
    left = Notification.objects.get(recipient=student_user, type=Notification.Type.TEAM_MEMBER_LEFT)
    assert joined.importance == Notification.Importance.NORMAL
    assert left.importance == Notification.Importance.NORMAL
    assert not Notification.objects.filter(recipient=student_two, type=Notification.Type.TEAM_MEMBER_JOINED).exists()


@pytest.mark.django_db
def test_member_removed_leadership_transferred_and_team_locked_notifications(
    student_user,
    student_two,
    year,
    user_factory,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    third = create_student(user_factory, "N-STU-003", "n-stu-003@example.com", year, "Student", "Three")
    team = TeamService.create_solo_team_for_student(student_user, year)
    invite_two = InvitationService.invite_student(team, student_two, student_user)
    invite_three = InvitationService.invite_student(team, third, student_user)
    InvitationService.accept_invitation(invite_two, student_two)
    InvitationService.accept_invitation(invite_three, third)

    ParticipationService.remove_member(team, third, student_user)
    ParticipationService.transfer_leadership(team, student_two, student_user)
    TeamService.lock_team(team, student_two)

    assert Notification.objects.filter(recipient=third, type=Notification.Type.TEAM_MEMBER_REMOVED).exists()
    assert Notification.objects.filter(recipient=student_two, type=Notification.Type.LEADERSHIP_TRANSFERRED).exists()
    assert Notification.objects.filter(type=Notification.Type.TEAM_LOCKED).count() == 2


@pytest.mark.django_db
def test_deliverable_uploaded_notifies_supervisors_and_leader_normal(
    student_user,
    student_two,
    teacher_user,
    year,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION)
    team = build_validated_team(year, student_user, teacher_user, member=student_two, code="N-DEL-UP")

    DeliverableFileService.upload_file(student_two, make_upload())

    recipients = set(Notification.objects.filter(type=Notification.Type.DELIVERABLE_UPLOADED).values_list("recipient", flat=True))
    assert recipients == {student_user.id, teacher_user.id}
    assert Notification.objects.get(recipient=student_user).importance == Notification.Importance.NORMAL


@pytest.mark.django_db
def test_deliverable_reviewed_notifies_team_members_important(student_user, student_two, teacher_user, year, monkeypatch):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION)
    team = build_validated_team(year, student_user, teacher_user, member=student_two, code="N-DEL-REV")
    deliverable = create_deliverable(team, student_user)

    DeliverableFileService.review_file(teacher_user, deliverable, DeliverableFile.ReviewStatus.ACCEPTED, "Good")

    notifications = Notification.objects.filter(type=Notification.Type.DELIVERABLE_REVIEWED)
    assert set(notifications.values_list("recipient", flat=True)) == {student_user.id, student_two.id}
    assert notifications.filter(importance=Notification.Importance.IMPORTANT).count() == 2


@pytest.mark.django_db
def test_subject_approved_and_rejected_are_important(student_user, teacher_user, teacher_two, year, monkeypatch):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)
    approved = Subject.objects.create(
        subject_code="N-SUB-APP",
        title="Subject approved",
        description="Subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=year,
    )
    rejected = Subject.objects.create(
        subject_code="N-SUB-REJ",
        title="Subject rejected",
        description="Subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=year,
    )

    SubjectWorkflowService.approve(approved, teacher_two)
    SubjectWorkflowService.reject(rejected, teacher_two, "Needs work")

    assert Notification.objects.get(type=Notification.Type.SUBJECT_APPROVED).importance == Notification.Importance.IMPORTANT
    assert Notification.objects.get(type=Notification.Type.SUBJECT_REJECTED).importance == Notification.Importance.IMPORTANT


@pytest.mark.django_db
def test_subject_submitted_and_resubmitted_are_important(teacher_user, year, monkeypatch):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)
    draft = Subject.objects.create(
        subject_code="N-SUB-SUB",
        title="Subject submitted",
        description="Subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=year,
    )
    rejected = Subject.objects.create(
        subject_code="N-SUB-RESUB",
        title="Subject resubmitted",
        description="Subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.REJECTED,
        proposed_by=teacher_user,
        academic_year=year,
    )

    SubjectWorkflowService.submit(draft)
    SubjectWorkflowService.resubmit(rejected)

    assert Notification.objects.get(type=Notification.Type.SUBJECT_SUBMITTED).importance == Notification.Importance.IMPORTANT
    assert Notification.objects.get(type=Notification.Type.SUBJECT_RESUBMITTED).importance == Notification.Importance.IMPORTANT


@pytest.mark.django_db
def test_assignment_result_available_notifies_team_members_important(
    student_user,
    student_two,
    teacher_user,
    admin_user,
    year,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1)
    team = Team.objects.create(team_code="N-ASSIGN", academic_year=year, name="Assign", status=Team.Status.LOCKED)
    TeamParticipant.objects.create(team=team, user=student_user, role=TeamParticipant.Role.LEADER, status=TeamParticipant.Status.ACTIVE)
    TeamParticipant.objects.create(team=team, user=student_two, role=TeamParticipant.Role.MEMBER, status=TeamParticipant.Status.ACTIVE)
    subject_for_team(team, teacher_user, year, status=Subject.Status.ASSIGNED, code="N-ASSIGN-SUB")

    AssignmentService.validate_assignment(admin_user, team)

    notifications = Notification.objects.filter(type=Notification.Type.ASSIGNMENT_RESULT_AVAILABLE)
    assert set(notifications.values_list("recipient", flat=True)) == {student_user.id, student_two.id}
    assert notifications.filter(importance=Notification.Importance.IMPORTANT).count() == 2


@pytest.mark.django_db
def test_appeal_notifications_cover_submission_acceptance_and_rejection(
    student_user,
    student_two,
    teacher_user,
    admin_user,
    year,
    user_factory,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS)
    accepted_team = build_validated_team(year, student_user, teacher_user, member=student_two, code="N-APP-ACC")
    appeal = AppealService.submit_appeal(accepted_team, student_user, "Please review")
    AppealService.accept_appeal(appeal, admin_user)

    other_leader = create_student(user_factory, "N-APP-LEAD", "n-app-lead@example.com", year)
    rejected_team = build_validated_team(year, other_leader, teacher_user, code="N-APP-REJ")
    rejected_appeal = AppealService.submit_appeal(rejected_team, other_leader, "Please reject")
    AppealService.reject_appeal(rejected_appeal, admin_user, "No")

    assert Notification.objects.filter(recipient=admin_user, type=Notification.Type.APPEAL_SUBMITTED).exists()
    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.APPEAL_ACCEPTED).exists()
    assert Notification.objects.filter(recipient=other_leader, type=Notification.Type.APPEAL_REJECTED).exists()


@pytest.mark.django_db
def test_defense_requested_scheduled_and_pv_notifications(
    student_user,
    teacher_user,
    teacher_two,
    admin_user,
    year,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.DEFENSE_WINDOW)
    team = build_validated_team(year, student_user, teacher_user, code="N-DEF")
    deliverable = create_deliverable(team, student_user)

    defense = DefenseService.request_defense(student_user, existing_file_ids=[deliverable.id])
    DefenseService.decide_supervisor(defense, teacher_user, "ACCEPTED")
    defense.refresh_from_db()
    DefenseService.schedule_defense(
        admin_user,
        defense,
        timezone.now() + timedelta(days=3),
        "Room N",
        teacher_two,
        [admin_user],
    )
    defense.refresh_from_db()
    DefenseService.upload_pv(admin_user, defense, Decimal("15.50"), "Passed", make_upload(name="pv.pdf"))

    assert Notification.objects.filter(recipient=teacher_user, type=Notification.Type.DEFENSE_REQUESTED).exists()
    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.DEFENSE_SCHEDULED).exists()
    assert Notification.objects.filter(recipient=teacher_two, type=Notification.Type.JURY_ASSIGNED).exists()
    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.PV_UPLOADED).exists()


@pytest.mark.django_db
def test_defense_supervisor_denied_and_ready_to_schedule_notifications(
    student_user,
    teacher_user,
    admin_user,
    year,
    user_factory,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.DEFENSE_WINDOW)
    team = build_validated_team(year, student_user, teacher_user, code="N-DEF-DENY")
    deliverable = create_deliverable(team, student_user)
    defense = DefenseService.request_defense(student_user, existing_file_ids=[deliverable.id])

    DefenseService.decide_supervisor(defense, teacher_user, "DENIED")

    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.DEFENSE_SUPERVISOR_DENIED).exists()

    next_leader = create_student(user_factory, "N-DEF-READY-STU", "n-def-ready@example.com", year)
    next_team = build_validated_team(year, next_leader, teacher_user, code="N-DEF-READY")
    next_deliverable = create_deliverable(next_team, next_leader)
    ready_defense = DefenseService.request_defense(next_leader, existing_file_ids=[next_deliverable.id])
    DefenseService.decide_supervisor(ready_defense, teacher_user, "ACCEPTED")

    assert Notification.objects.filter(recipient=next_leader, type=Notification.Type.DEFENSE_SUPERVISOR_ACCEPTED).exists()
    assert Notification.objects.filter(recipient=admin_user, type=Notification.Type.DEFENSE_READY_TO_SCHEDULE).exists()


@pytest.mark.django_db
def test_academic_year_closed_and_archived_notify_admins_only(
    super_admin_user,
    admin_user,
    student_user,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    year = create_year(label="2030/2031")

    AcademicYearLifecycleService.close_year(super_admin_user, year, "Closing", confirm=True)
    year.refresh_from_db()
    AcademicYearLifecycleService.archive_year(super_admin_user, year, "Archive", confirm=True)

    assert Notification.objects.filter(recipient=admin_user, type=Notification.Type.ACADEMIC_YEAR_CLOSED).exists()
    assert Notification.objects.filter(recipient=super_admin_user, type=Notification.Type.ACADEMIC_YEAR_ARCHIVED).exists()
    assert not Notification.objects.filter(recipient=student_user, type__startswith="ACADEMIC_YEAR").exists()


@pytest.mark.django_db
def test_archived_year_student_notification_is_skipped_but_admin_allowed(student_user, admin_user, monkeypatch):
    mute_email_enqueue(monkeypatch)
    archived_year = create_year(label="2020/2021", status=AcademicYear.Status.ARCHIVED)

    skipped = NotificationService.notify_user(
        student_user,
        Notification.Type.TEAM_LOCKED,
        "Archived",
        "Should skip.",
        Notification.Importance.NORMAL,
        academic_year=archived_year,
    )
    allowed = NotificationService.notify_user(
        admin_user,
        Notification.Type.ACADEMIC_YEAR_ARCHIVED,
        "Archived",
        "Admin allowed.",
        Notification.Importance.IMPORTANT,
        academic_year=archived_year,
    )

    assert skipped is None
    assert allowed is not None


@pytest.mark.django_db
def test_duplicate_recipients_receive_one_notification_and_actor_excluded(
    student_user,
    teacher_user,
    year,
    monkeypatch,
):
    mute_email_enqueue(monkeypatch)
    open_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION)
    NotificationService.notify_many(
        [student_user, student_user],
        Notification.Type.TEAM_LOCKED,
        "One",
        "Deduped.",
        Notification.Importance.NORMAL,
        academic_year=year,
    )
    team = build_validated_team(year, student_user, teacher_user, code="N-DUP")
    deliverable = create_deliverable(team, student_user)
    comment = DeliverableFileService.add_comment(student_user, deliverable, "Author excluded")

    assert Notification.objects.filter(recipient=student_user, type=Notification.Type.TEAM_LOCKED).count() == 1
    assert comment is not None
    assert not Notification.objects.filter(
        recipient=student_user,
        type=Notification.Type.DELIVERABLE_COMMENT_ADDED,
    ).exists()
    assert Notification.objects.filter(
        recipient=teacher_user,
        type=Notification.Type.DELIVERABLE_COMMENT_ADDED,
    ).exists()
