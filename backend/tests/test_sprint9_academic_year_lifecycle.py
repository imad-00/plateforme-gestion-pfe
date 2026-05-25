from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PlatformAccessGrant, User
from apps.academics.models import AcademicYear
from apps.archives.models import AcademicYearLifecycleEvent
from apps.archives.services import AcademicYearLifecycleService
from apps.assignments.models import Appeal
from apps.assignments.services import AssignmentService
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.defenses.models import Defense
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_upload(name="archive.txt", content=b"archive", content_type="text/plain"):
    return SimpleUploadedFile(name=name, content=content, content_type=content_type)


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def open_phase(year, phase_type, order=1):
    now = timezone.now()
    return CampaignPhase.objects.create(
        academic_year=year,
        phase_type=phase_type,
        start_at=now - timedelta(days=1),
        end_at=None,
        display_order=order,
    )


def approved_subject(teacher, year, code="S9-SUBJECT"):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Lifecycle subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher,
        academic_year=year,
    )


def build_validated_team(student, teacher, admin, year, code="S9-VALIDATED"):
    open_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, order=1)
    team = TeamService.create_solo_team_for_student(student, year)
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    subject = approved_subject(teacher, year, code=code)
    AssignmentService.manual_assign(admin, team, subject)
    AssignmentService.validate_assignment(admin, team)
    return team, subject


def close_payload(reason="End of campaign", force=False):
    return {"reason": reason, "confirm": True, "force": force}


@pytest.mark.django_db
def test_non_super_admin_cannot_close_academic_year(admin_user):
    year = create_year()

    response = auth_client(admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_super_admin_can_get_closure_readiness(super_admin_user, student_user):
    year = create_year()
    TeamService.create_solo_team_for_student(student_user, year)

    response = auth_client(super_admin_user).get(
        f"/api/super-admin/academic-years/{year.id}/closure-readiness/"
    )

    assert response.status_code == 200
    assert response.json()["academic_year"]["id"] == year.id
    assert "FORMING_TEAMS" in {warning["code"] for warning in response.json()["warnings"]}


@pytest.mark.django_db
def test_closing_requires_confirm_and_reason(super_admin_user):
    year = create_year()
    client = auth_client(super_admin_user)

    missing_confirm = client.post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        {"reason": "End", "confirm": False},
        format="json",
    )
    missing_reason = client.post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        {"reason": "", "confirm": True},
        format="json",
    )

    assert missing_confirm.status_code == 400
    assert missing_reason.status_code == 400


@pytest.mark.django_db
def test_normal_close_dissolves_forming_and_locked_teams_and_ends_participants(super_admin_user, student_user, user_factory):
    year = create_year()
    forming = TeamService.create_solo_team_for_student(student_user, year)
    locked_student = user_factory(
        matricule="S9LOCK001",
        email="s9-lock@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )
    locked = TeamService.create_solo_team_for_student(locked_student, year)
    locked.status = Team.Status.LOCKED
    locked.save(update_fields=["status", "updated_at"])

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )

    assert response.status_code == 200
    forming.refresh_from_db()
    locked.refresh_from_db()
    assert forming.status == Team.Status.DISSOLVED
    assert locked.status == Team.Status.DISSOLVED
    assert not TeamParticipant.objects.filter(team__in=[forming, locked], status=TeamParticipant.Status.ACTIVE).exists()


@pytest.mark.django_db
def test_normal_close_blocks_validated_team_without_completed_defense(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
):
    year = create_year()
    build_validated_team(student_user, teacher_user, admin_user, year)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )

    assert response.status_code == 400
    year.refresh_from_db()
    assert year.status == AcademicYear.Status.ACTIVE


@pytest.mark.django_db
def test_force_close_allows_unresolved_validated_team_and_keeps_status(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(force=True),
        format="json",
    )

    assert response.status_code == 200
    year.refresh_from_db()
    team.refresh_from_db()
    assert year.status == AcademicYear.Status.CLOSED
    assert team.status == Team.Status.VALIDATED
    assert AcademicYearLifecycleEvent.objects.filter(
        academic_year=year,
        event_type=AcademicYearLifecycleEvent.EventType.FORCE_CLOSED,
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "defense_status",
    [Defense.Status.REQUESTED, Defense.Status.READY_TO_SCHEDULE, Defense.Status.SCHEDULED],
)
def test_normal_close_blocks_unresolved_defense_statuses(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
    defense_status,
):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    Defense.objects.create(
        team=team,
        status=defense_status,
        requested_by=student_user,
        requested_at=timezone.now(),
    )

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_force_close_keeps_requested_defense_status(super_admin_user, student_user, teacher_user, admin_user):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    defense = Defense.objects.create(
        team=team,
        status=Defense.Status.REQUESTED,
        requested_by=student_user,
        requested_at=timezone.now(),
    )

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(force=True),
        format="json",
    )

    assert response.status_code == 200
    defense.refresh_from_db()
    assert defense.status == Defense.Status.REQUESTED


@pytest.mark.django_db
def test_completed_defense_remains_completed_after_close_and_archive(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    defense = Defense.objects.create(
        team=team,
        status=Defense.Status.COMPLETED,
        requested_by=student_user,
        requested_at=timezone.now(),
        final_grade="15.00",
        deliberation="Passed",
        pv_uploaded_by=admin_user,
        pv_uploaded_at=timezone.now(),
    )

    close_response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )
    archive_response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/archive/",
        {"reason": "Historical archive", "confirm": True},
        format="json",
    )

    defense.refresh_from_db()
    team.refresh_from_db()
    assert close_response.status_code == 200
    assert archive_response.status_code == 200
    assert defense.status == Defense.Status.COMPLETED
    assert team.status == Team.Status.VALIDATED


@pytest.mark.django_db
def test_pending_appeal_blocks_normal_close_and_force_close_keeps_status(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    appeal = Appeal.objects.create(team=team, reason="Pending", status=Appeal.Status.PENDING, submitted_by=student_user)

    blocked = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )
    forced = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(force=True),
        format="json",
    )

    appeal.refresh_from_db()
    assert blocked.status_code == 400
    assert forced.status_code == 200
    assert appeal.status == Appeal.Status.PENDING


@pytest.mark.django_db
def test_closing_freezes_open_phases_and_campaign_phase_service_returns_closed(super_admin_user):
    year = create_year()
    phase = open_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(),
        format="json",
    )

    phase.refresh_from_db()
    year.refresh_from_db()
    assert response.status_code == 200
    assert phase.end_at is not None
    assert not CampaignPhaseService.is_open(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    with pytest.raises(Exception):
        CampaignPhaseService.require_open(year, CampaignPhase.PhaseType.TEAM_FORMATION)


@pytest.mark.django_db
def test_writes_fail_for_closed_year(super_admin_user, student_user, teacher_user, admin_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION, order=2)
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(force=True),
        format="json",
    )

    upload = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload()},
        format="multipart",
    )
    admin_remove = auth_client(admin_user).post(
        f"/api/admin/teams/{team.pk}/dissolve/",
        {},
        format="json",
    )

    assert upload.status_code == 400
    assert admin_remove.status_code == 400


@pytest.mark.django_db
def test_reopen_closed_year_requires_super_admin_and_does_not_reopen_phases(super_admin_user, admin_user):
    year = create_year()
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.TEAM_FORMATION,
        start_at=timezone.now() - timedelta(days=2),
        end_at=timezone.now() - timedelta(days=1),
        display_order=1,
    )
    year.status = AcademicYear.Status.CLOSED
    year.save(update_fields=["status", "updated_at"])

    forbidden = auth_client(admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/reopen/",
        {"reason": "Need corrections", "confirm": True},
        format="json",
    )
    allowed = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/reopen/",
        {"reason": "Need corrections", "confirm": True},
        format="json",
    )

    year.refresh_from_db()
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert year.status == AcademicYear.Status.ACTIVE
    assert CampaignPhaseService.get_open_phases(year) == []


@pytest.mark.django_db
def test_reopen_fails_if_another_year_is_active(super_admin_user):
    closed = create_year("2024/2025", AcademicYear.Status.CLOSED)
    create_year("2025/2026", AcademicYear.Status.ACTIVE)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{closed.id}/reopen/",
        {"reason": "Cannot overlap", "confirm": True},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_reopen_archived_or_archive_active_year(super_admin_user):
    archived = create_year("2024/2025", AcademicYear.Status.ARCHIVED)
    active = create_year("2025/2026", AcademicYear.Status.ACTIVE)
    client = auth_client(super_admin_user)

    reopen = client.post(
        f"/api/super-admin/academic-years/{archived.id}/reopen/",
        {"reason": "No", "confirm": True},
        format="json",
    )
    archive = client.post(
        f"/api/super-admin/academic-years/{active.id}/archive/",
        {"reason": "No", "confirm": True},
        format="json",
    )

    assert reopen.status_code == 400
    assert archive.status_code == 400


@pytest.mark.django_db
def test_archive_suspends_only_students_and_external_supervisors_linked_only_to_year(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
    user_factory,
):
    year = create_year(status=AcademicYear.Status.CLOSED)
    student_user.student_profile.academic_year = year
    student_user.student_profile.save(update_fields=["academic_year", "updated_at"])
    external = user_factory(
        matricule="S9EXT001",
        email="s9-ext@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
    )
    team = Team.objects.create(academic_year=year, name="Archived supervised team", status=Team.Status.VALIDATED)
    TeamParticipant.objects.create(team=team, user=external, role=TeamParticipant.Role.SUPERVISOR, status=TeamParticipant.Status.ACTIVE)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/archive/",
        {"reason": "Archive complete", "confirm": True},
        format="json",
    )

    student_user.refresh_from_db()
    external.refresh_from_db()
    teacher_user.refresh_from_db()
    admin_user.refresh_from_db()
    assert response.status_code == 200
    assert student_user.account_status == User.AccountStatus.SUSPENDED
    assert external.account_status == User.AccountStatus.SUSPENDED
    assert teacher_user.account_status == User.AccountStatus.ACTIVE
    assert admin_user.account_status == User.AccountStatus.ACTIVE


@pytest.mark.django_db
def test_archive_does_not_suspend_external_supervisor_linked_to_another_active_year(
    super_admin_user,
    user_factory,
):
    closed_year = create_year("2024/2025", AcademicYear.Status.CLOSED)
    active_year = create_year("2025/2026", AcademicYear.Status.ACTIVE)
    external = user_factory(
        matricule="S9EXT002",
        email="s9-ext2@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
    )
    closed_team = Team.objects.create(academic_year=closed_year, name="Closed team", status=Team.Status.VALIDATED)
    active_team = Team.objects.create(academic_year=active_year, name="Active team", status=Team.Status.VALIDATED)
    TeamParticipant.objects.create(team=closed_team, user=external, role=TeamParticipant.Role.SUPERVISOR, status=TeamParticipant.Status.ACTIVE)
    TeamParticipant.objects.create(team=active_team, user=external, role=TeamParticipant.Role.SUPERVISOR, status=TeamParticipant.Status.ACTIVE)

    response = auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{closed_year.id}/archive/",
        {"reason": "Archive closed year", "confirm": True},
        format="json",
    )

    external.refresh_from_db()
    assert response.status_code == 200
    assert external.account_status == User.AccountStatus.ACTIVE


@pytest.mark.django_db
def test_archived_year_data_is_readable_only_by_platform_admin(
    super_admin_user,
    student_user,
    teacher_user,
    admin_user,
):
    year = create_year()
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year)
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(),
        original_filename="archive.txt",
        file_size=7,
        content_type="text/plain",
        uploaded_by=student_user,
    )
    auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/close/",
        close_payload(force=True),
        format="json",
    )
    auth_client(super_admin_user).post(
        f"/api/super-admin/academic-years/{year.id}/archive/",
        {"reason": "Archive", "confirm": True},
        format="json",
    )

    teacher_response = auth_client(teacher_user).get(f"/api/deliverable-files/{deliverable.id}/")
    admin_response = auth_client(admin_user).get(f"/api/admin/teams/{team.pk}/")

    assert teacher_response.status_code == 403
    assert admin_response.status_code == 200


@pytest.mark.django_db
def test_lifecycle_events_created_for_close_reopen_and_archive(super_admin_user):
    year = create_year()
    client = auth_client(super_admin_user)

    client.post(f"/api/super-admin/academic-years/{year.id}/close/", close_payload(), format="json")
    client.post(
        f"/api/super-admin/academic-years/{year.id}/reopen/",
        {"reason": "Reopen", "confirm": True},
        format="json",
    )
    client.post(f"/api/super-admin/academic-years/{year.id}/close/", close_payload(), format="json")
    client.post(
        f"/api/super-admin/academic-years/{year.id}/archive/",
        {"reason": "Archive", "confirm": True},
        format="json",
    )

    assert AcademicYearLifecycleEvent.objects.filter(academic_year=year).count() == 4
    assert set(AcademicYearLifecycleEvent.objects.filter(academic_year=year).values_list("event_type", flat=True)) == {
        AcademicYearLifecycleEvent.EventType.CLOSED,
        AcademicYearLifecycleEvent.EventType.REOPENED,
        AcademicYearLifecycleEvent.EventType.ARCHIVED,
    }


@pytest.mark.django_db
def test_creating_new_academic_year_requires_super_admin_and_previous_not_active(admin_user, super_admin_user):
    active = create_year()

    admin_forbidden = auth_client(admin_user).post(
        "/api/admin/academic-years/",
        {"year": "2026/2027", "status": AcademicYear.Status.CLOSED},
        format="json",
    )
    super_blocked = auth_client(super_admin_user).post(
        "/api/admin/academic-years/",
        {"year": "2026/2027", "status": AcademicYear.Status.CLOSED},
        format="json",
    )
    active.status = AcademicYear.Status.CLOSED
    active.save(update_fields=["status", "updated_at"])
    super_allowed = auth_client(super_admin_user).post(
        "/api/admin/academic-years/",
        {"year": "2026/2027", "status": AcademicYear.Status.ACTIVE},
        format="json",
    )

    assert admin_forbidden.status_code == 403
    assert super_blocked.status_code == 400
    assert super_allowed.status_code == 201


@pytest.mark.django_db
def test_admin_archive_endpoint_no_longer_bypasses_lifecycle_rules(admin_user, super_admin_user):
    active = create_year()
    closed = create_year("2024/2025", AcademicYear.Status.CLOSED)

    admin_forbidden = auth_client(admin_user).post(
        f"/api/admin/academic-years/{closed.id}/archive/",
        {"reason": "No", "confirm": True},
        format="json",
    )
    missing_confirm = auth_client(super_admin_user).post(
        f"/api/admin/academic-years/{closed.id}/archive/",
        {},
        format="json",
    )
    active_archive = auth_client(super_admin_user).post(
        f"/api/admin/academic-years/{active.id}/archive/",
        {"reason": "No", "confirm": True},
        format="json",
    )

    assert admin_forbidden.status_code == 403
    assert missing_confirm.status_code == 400
    assert active_archive.status_code == 400


@pytest.mark.django_db
def test_platform_admin_access_still_uses_platform_access_grants(super_admin_user, user_factory):
    year = create_year(status=AcademicYear.Status.CLOSED)
    teacher_admin = user_factory(
        matricule="S9TADMIN",
        email="s9-teacher-admin@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
    )
    PlatformAccessGrant.objects.create(
        user=teacher_admin,
        access_level=PlatformAccessGrant.AccessLevel.ADMIN,
        granted_by=super_admin_user,
    )

    with pytest.raises(Exception):
        AcademicYearLifecycleService.archive_year(
            teacher_admin,
            year,
            reason="Admin is not super-admin",
            confirm=True,
        )
