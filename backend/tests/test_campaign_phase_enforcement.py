from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import StudentProfile, User
from apps.academics.models import AcademicYear
from apps.assignments.models import Appeal
from apps.assignments.services import AssignmentService, WishListService
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def open_phase(year, phase_type, order=1, days_before=1, days_after=1):
    now = timezone.now()
    return CampaignPhase.objects.create(
        academic_year=year,
        phase_type=phase_type,
        start_at=now - timedelta(days=days_before),
        end_at=now + timedelta(days=days_after) if days_after is not None else None,
        display_order=order,
    )


def approve_subject(teacher, year, code="PH-SUB", subject_type=Subject.SubjectType.APPLIED_PROJECT):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Approved subject",
        subject_type=subject_type,
        status=Subject.Status.APPROVED,
        proposed_by=teacher,
        academic_year=year,
    )


def locked_solo_team(student, year):
    team = TeamService.create_solo_team_for_student(student, year)
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    return team


def submit_one_subject_wishlist(team, actor, subject, selection_round=Team.SelectionRound.FIRST):
    return WishListService.submit_wishlist(
        team,
        actor,
        selection_round,
        [{"subject_id": subject.id, "rank": 1}],
    )


@pytest.mark.django_db
def test_phase_service_respects_window_and_allows_overlapping_phases():
    year = create_year()
    now = timezone.now()
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.TEAM_FORMATION,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
        display_order=1,
    )
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
        start_at=now - timedelta(hours=1),
        end_at=None,
        display_order=2,
    )
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.WISHLIST_1,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        display_order=3,
    )
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.RESULTS_AND_APPEALS,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        display_order=4,
    )

    assert CampaignPhaseService.is_open(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    assert CampaignPhaseService.is_open(year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)
    assert not CampaignPhaseService.is_open(year, CampaignPhase.PhaseType.WISHLIST_1)
    assert not CampaignPhaseService.is_open(year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS)
    assert set(CampaignPhaseService.get_open_phases(year)) == {
        CampaignPhase.PhaseType.TEAM_FORMATION,
        CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
    }


@pytest.mark.django_db
def test_student_creation_without_active_academic_year_fails_cleanly(admin_user):
    response = auth_client(admin_user).post(
        "/api/admin/users/",
        {
            "matricule": "NOYEAR001",
            "email": "noyear001@example.com",
            "password": "Testpass123!",
            "business_identity": User.BusinessIdentity.STUDENT,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "No active academic year" in str(response.json())


@pytest.mark.django_db
def test_student_creation_assigns_active_academic_year(admin_user):
    year = create_year()

    response = auth_client(admin_user).post(
        "/api/admin/users/",
        {
            "matricule": "ACTIVEYEAR001",
            "email": "activeyear001@example.com",
            "password": "Testpass123!",
            "business_identity": User.BusinessIdentity.STUDENT,
        },
        format="json",
    )

    assert response.status_code == 201
    student = User.objects.get(matricule="ACTIVEYEAR001")
    assert student.student_profile.academic_year_id == year.id
    assert TeamService.get_active_student_team(student).academic_year_id == year.id


@pytest.mark.django_db
def test_student_team_actions_require_team_formation_phase(student_user, user_factory):
    year = create_year()
    student_two = user_factory(
        matricule="PHSTU002",
        email="ph-student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )
    team = TeamService.create_solo_team_for_student(student_user, year)

    response = auth_client(student_user).post(
        f"/api/teams/{team.pk}/invite/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 400
    assert "team formation phase" in str(response.json()).lower()


@pytest.mark.django_db
def test_admin_team_override_still_works_outside_team_formation(admin_user, student_user, user_factory):
    year = create_year()
    student_two = user_factory(
        matricule="PHSTU003",
        email="ph-student3@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )
    team = TeamService.create_solo_team_for_student(student_user, year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
    )

    response = auth_client(admin_user).post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_teacher_subject_creation_requires_subject_management_phase(teacher_user):
    create_year()

    response = auth_client(teacher_user).post(
        "/api/teacher/subjects/",
        {
            "title": "Phase gated topic",
            "description": "Should be blocked while subject phase is closed.",
            "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "subject management phase" in str(response.json()).lower()


@pytest.mark.django_db
def test_subject_creation_succeeds_when_subject_management_phase_is_open(teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)

    response = auth_client(teacher_user).post(
        "/api/teacher/subjects/",
        {
            "title": "Open phase topic",
            "description": "Subject management is open.",
            "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        },
        format="json",
    )

    assert response.status_code == 201
    assert Subject.objects.get(id=response.json()["id"]).academic_year_id == year.id


@pytest.mark.django_db
def test_catalog_hidden_until_wishlist_phase_opens(student_user, teacher_user):
    year = create_year()
    locked_solo_team(student_user, year)
    approve_subject(teacher_user, year)

    response = auth_client(student_user).get("/api/subjects/catalog/")

    assert response.status_code == 400
    assert "catalog" in str(response.json()).lower()


@pytest.mark.django_db
def test_catalog_visible_during_first_wishlist_phase(student_user, teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.WISHLIST_1)
    locked_solo_team(student_user, year)
    subject = approve_subject(teacher_user, year)

    response = auth_client(student_user).get("/api/subjects/catalog/")

    assert response.status_code == 200
    assert subject.id in {item["id"] for item in response.json()["results"]}


@pytest.mark.django_db
def test_second_wishlist_catalog_requires_accepted_appeal(student_user, teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.WISHLIST_2)
    team = locked_solo_team(student_user, year)
    team.selection_round = Team.SelectionRound.SECOND
    team.save(update_fields=["selection_round", "updated_at"])
    approve_subject(teacher_user, year)

    blocked = auth_client(student_user).get("/api/subjects/catalog/")
    assert blocked.status_code == 400

    Appeal.objects.create(
        team=team,
        reason="Accepted appeal",
        status=Appeal.Status.ACCEPTED,
        submitted_by=student_user,
    )
    allowed = auth_client(student_user).get("/api/subjects/catalog/")
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_wishlist_rejects_cross_academic_year_subject(student_user, teacher_user):
    active_year = create_year()
    other_year = create_year("2024/2025", AcademicYear.Status.CLOSED)
    open_phase(active_year, CampaignPhase.PhaseType.WISHLIST_1)
    team = locked_solo_team(student_user, active_year)
    other_subject = approve_subject(teacher_user, other_year, code="OTHER-YEAR")

    with pytest.raises(Exception) as excinfo:
        submit_one_subject_wishlist(team, student_user, other_subject)

    assert "academic year" in str(excinfo.value).lower() or "unavailable" in str(excinfo.value).lower()


@pytest.mark.django_db
def test_forming_team_auto_locks_only_after_successful_wishlist_validation(student_user, teacher_user):
    year = create_year()
    year.wishlist_size = 2
    year.save(update_fields=["wishlist_size", "updated_at"])
    open_phase(year, CampaignPhase.PhaseType.WISHLIST_1)
    team = TeamService.create_solo_team_for_student(student_user, year)
    subject = approve_subject(teacher_user, year, code="ONE-ONLY")
    approve_subject(teacher_user, year, code="SECOND-AVAILABLE")

    response = auth_client(student_user).post(
        "/api/wishlists/",
        {"selection_round": Team.SelectionRound.FIRST, "items": [{"subject_id": subject.id, "rank": 1}]},
        format="json",
    )

    assert response.status_code == 400
    team.refresh_from_db()
    assert team.status == Team.Status.FORMING


@pytest.mark.django_db
def test_assignment_rejects_subject_from_different_academic_year(admin_user, student_user, teacher_user):
    active_year = create_year()
    other_year = create_year("2024/2025", AcademicYear.Status.CLOSED)
    open_phase(active_year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1)
    team = locked_solo_team(student_user, active_year)
    subject = approve_subject(teacher_user, other_year, code="ASSIGN-OTHER-YEAR")

    with pytest.raises(Exception) as excinfo:
        AssignmentService.manual_assign(admin_user, team, subject)

    assert "same academic year" in str(excinfo.value).lower()


@pytest.mark.django_db
def test_assignment_requires_review_phase(admin_user, student_user, teacher_user):
    year = create_year()
    team = locked_solo_team(student_user, year)
    subject = approve_subject(teacher_user, year, code="NO-REVIEW")

    with pytest.raises(Exception) as excinfo:
        AssignmentService.manual_assign(admin_user, team, subject)

    assert "assignment review phase" in str(excinfo.value).lower()


@pytest.mark.django_db
def test_assignment_reserves_subject_then_validation_marks_team_validated(admin_user, student_user, teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1)
    team = locked_solo_team(student_user, year)
    subject = approve_subject(teacher_user, year, code="VALIDATE-ME")

    AssignmentService.manual_assign(admin_user, team, subject)
    team.refresh_from_db()
    subject.refresh_from_db()
    assert team.status == Team.Status.LOCKED
    assert team.assignment_validated_at is None
    assert subject.status == Subject.Status.ASSIGNED
    assert subject.assigned_to_team_id == team.pk

    response = auth_client(admin_user).post(f"/api/admin/assignments/{team.pk}/validate/", {}, format="json")

    assert response.status_code == 200
    team.refresh_from_db()
    assert team.status == Team.Status.VALIDATED
    assert team.assignment_validated_at is not None
    assert team.assignment_validated_by_id == admin_user.id
    assert TeamParticipant.objects.filter(
        team=team,
        user=teacher_user,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    ).exists()


@pytest.mark.django_db
def test_student_assignment_result_visibility_requires_results_phase(admin_user, student_user, teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1)
    team = locked_solo_team(student_user, year)
    subject = approve_subject(teacher_user, year, code="RESULT-PHASE")
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)

    blocked = auth_client(student_user).get("/api/assignments/me/")
    assert blocked.status_code == 403

    open_phase(year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS, order=2)
    visible = auth_client(student_user).get("/api/assignments/me/")
    assert visible.status_code == 200
    assert visible.json()["subject_id"] == subject.id


@pytest.mark.django_db
def test_appeal_actions_require_results_and_appeals_phase(admin_user, student_user, teacher_user):
    year = create_year()
    open_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1)
    team = locked_solo_team(student_user, year)
    subject = approve_subject(teacher_user, year, code="APPEAL-PHASE")
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)

    blocked_submit = auth_client(student_user).post("/api/appeals/", {"reason": "Not satisfied"}, format="json")
    assert blocked_submit.status_code == 400

    open_phase(year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS, order=2)
    appeal = Appeal.objects.create(team=team, reason="Pending", status=Appeal.Status.PENDING, submitted_by=student_user)
    accepted = auth_client(admin_user).post(f"/api/admin/appeals/{appeal.pk}/accept/", {}, format="json")
    assert accepted.status_code == 200
    team.refresh_from_db()
    subject.refresh_from_db()
    assert team.status == Team.Status.LOCKED
    assert team.selection_round == Team.SelectionRound.SECOND
    assert team.assignment_validated_at is None
    assert subject.status == Subject.Status.APPROVED
    assert subject.assigned_to_team_id is None


@pytest.mark.django_db
def test_missing_annual_average_defaults_to_ten(student_user, user_factory):
    year = create_year()
    student_two = user_factory(
        matricule="AVG002",
        email="avg002@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )
    StudentProfile.objects.filter(user=student_user).update(academic_year=year, annual_average=Decimal("16.00"))
    StudentProfile.objects.filter(user=student_two).update(academic_year=year, annual_average=None)
    team = TeamService.create_solo_team_for_student(student_user, year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
    )

    average = AssignmentService.compute_team_average(team)

    assert average == Decimal("13.00")
