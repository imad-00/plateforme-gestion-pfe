from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.academics.models import AcademicYear
from apps.accounts.models import User
from apps.assignments.models import Appeal
from apps.defenses.models import Defense, DefenseJuryAssignment, DefenseSupervisorDecision
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def set_student_year(student, year):
    student.student_profile.academic_year = year
    student.student_profile.save(update_fields=["academic_year", "updated_at"])


def create_student(user_factory, matricule, year, first_name="Student", last_name="One"):
    student = user_factory(
        matricule=matricule,
        email=f"{matricule.lower()}@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
        first_name=first_name,
        last_name=last_name,
    )
    set_student_year(student, year)
    return student


def create_teacher(user_factory, matricule="T-DASH", identity=User.BusinessIdentity.TEACHER):
    return user_factory(
        matricule=matricule,
        email=f"{matricule.lower()}@example.com",
        business_identity=identity,
        first_name="Teacher",
        last_name=matricule,
    )


def create_team(year, code, status=Team.Status.VALIDATED, leader=None, member=None, supervisor=None):
    team = Team.objects.create(
        team_code=code,
        academic_year=year,
        name=f"Team {code}",
        status=status,
        selection_round=Team.SelectionRound.FIRST,
        annual_average=Decimal("12.50"),
    )
    if leader is not None:
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
    if supervisor is not None:
        TeamParticipant.objects.create(
            team=team,
            user=supervisor,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
            joined_at=timezone.now(),
        )
    return team


def assign_subject(team, teacher, code):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Dashboard subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.ASSIGNED,
        proposed_by=teacher,
        academic_year=team.academic_year,
        assigned_to_team=team,
    )


def create_deliverable(team, uploader, *, status=DeliverableFile.ReviewStatus.PENDING, name="dash.txt"):
    return DeliverableFile.objects.create(
        team=team,
        file=f"deliverables/{team.pk}/{name}",
        original_filename=name,
        file_size=10,
        content_type="text/plain",
        uploaded_by=uploader,
        review_status=status,
    )


def create_defense(team, requester, status=Defense.Status.SCHEDULED, scheduled_at=None):
    return Defense.objects.create(
        team=team,
        status=status,
        requested_by=requester,
        requested_at=timezone.now() - timedelta(days=1),
        scheduled_at=scheduled_at,
        location="Room A" if scheduled_at else "",
    )


@pytest.mark.django_db
def test_unauthenticated_user_cannot_access_dashboards():
    client = APIClient()

    assert client.get("/api/dashboard/admin/").status_code == 401
    assert client.get("/api/dashboard/teacher/").status_code == 401
    assert client.get("/api/dashboard/student/").status_code == 401


@pytest.mark.django_db
def test_student_and_teacher_without_grant_cannot_access_admin_dashboard(student_user, teacher_user):
    assert auth_client(student_user).get("/api/dashboard/admin/").status_code == 403
    assert auth_client(teacher_user).get("/api/dashboard/admin/").status_code == 403


@pytest.mark.django_db
def test_admin_dashboard_counts_campaign_entities(admin_user, teacher_user, user_factory):
    year = create_year()
    leader = create_student(user_factory, "D-STU-001", year)
    member = create_student(user_factory, "D-STU-002", year)
    forming = create_team(year, "D-FORM", Team.Status.FORMING)
    locked = create_team(year, "D-LOCK", Team.Status.LOCKED)
    validated = create_team(year, "D-VAL", Team.Status.VALIDATED, leader=leader, member=member, supervisor=teacher_user)
    dissolved = create_team(year, "D-DIS", Team.Status.DISSOLVED)
    assign_subject(validated, teacher_user, "D-SUB-ASSIGNED")
    Subject.objects.create(
        subject_code="D-SUB-DRAFT",
        title="Draft subject",
        description="Draft",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=year,
    )
    create_defense(validated, leader, Defense.Status.REQUESTED)
    create_defense(locked, leader, Defense.Status.SCHEDULED, timezone.now() + timedelta(days=2))
    completed = create_defense(dissolved, leader, Defense.Status.COMPLETED, timezone.now() - timedelta(days=2))
    completed.final_grade = Decimal("16.00")
    completed.pv_uploaded_at = timezone.now()
    completed.save(update_fields=["final_grade", "pv_uploaded_at", "updated_at"])
    Appeal.objects.create(team=validated, reason="Pending", submitted_by=leader)
    Appeal.objects.create(team=locked, reason="Accepted", status=Appeal.Status.ACCEPTED, submitted_by=leader)
    create_deliverable(validated, leader, status=DeliverableFile.ReviewStatus.PENDING)
    create_deliverable(validated, member, status=DeliverableFile.ReviewStatus.ACCEPTED, name="accepted.txt")
    other_year = create_year("2024/2025", status=AcademicYear.Status.CLOSED)
    create_team(other_year, "D-OTHER", Team.Status.VALIDATED)

    response = auth_client(admin_user).get("/api/dashboard/admin/")

    assert response.status_code == 200
    data = response.json()
    assert data["teams"] == {
        "total": 4,
        "forming": 1,
        "locked": 1,
        "validated": 1,
        "dissolved": 1,
    }
    assert data["assignments"] == {"assigned": 1, "unassigned": 3}
    assert data["defenses"]["requested"] == 1
    assert data["defenses"]["scheduled"] == 1
    assert data["defenses"]["completed"] == 1
    assert data["appeals"]["pending_or_submitted"] == 1
    assert data["appeals"]["accepted"] == 1
    assert data["deliverables"]["pending_review"] == 1
    assert data["deliverables"]["accepted"] == 1
    assert data["subjects"]["draft"] == 1
    assert data["subjects"]["assigned"] == 1


@pytest.mark.django_db
def test_admin_dashboard_can_view_archived_academic_year(admin_user):
    archived = create_year("2020/2021", status=AcademicYear.Status.ARCHIVED)
    create_team(archived, "D-ARCH", Team.Status.DISSOLVED)

    response = auth_client(admin_user).get(f"/api/dashboard/admin/?academic_year_id={archived.id}")

    assert response.status_code == 200
    assert response.json()["academic_year"]["status"] == AcademicYear.Status.ARCHIVED
    assert response.json()["teams"]["dissolved"] == 1


@pytest.mark.django_db
def test_teacher_dashboard_counts_supervision_deliverables_and_upcoming_defenses(
    teacher_user,
    admin_user,
    user_factory,
):
    year = create_year()
    leader = create_student(user_factory, "D-TEACH-STU", year)
    team = create_team(year, "D-TEACH", Team.Status.VALIDATED, leader=leader, supervisor=teacher_user)
    create_deliverable(team, leader)
    defense = create_defense(team, leader, Defense.Status.SCHEDULED, timezone.now() + timedelta(days=3))
    DefenseJuryAssignment.objects.create(
        defense=defense,
        user=admin_user,
        role=DefenseJuryAssignment.JuryRole.EXAMINER,
        assigned_by=admin_user,
    )
    pending_defense = create_defense(team, leader, Defense.Status.REQUESTED)
    DefenseSupervisorDecision.objects.create(defense=pending_defense, supervisor=teacher_user)

    response = auth_client(teacher_user).get("/api/dashboard/teacher/")

    assert response.status_code == 200
    data = response.json()
    assert data["supervision"]["supervised_teams_count"] == 1
    assert data["supervision"]["validated_supervised_teams_count"] == 1
    assert data["deliverables"]["pending_review_count"] == 1
    assert data["deliverables"]["latest_pending_review"][0]["team_code"] == team.pk
    assert data["defenses"]["upcoming_count"] == 1
    assert data["defenses"]["pending_requests_count"] == 1
    assert data["defenses"]["upcoming"][0]["role_context"] == "SUPERVISOR"


@pytest.mark.django_db
def test_teacher_cannot_access_archived_year_unless_admin(teacher_user, admin_user):
    archived = create_year("2021/2022", status=AcademicYear.Status.ARCHIVED)

    assert auth_client(teacher_user).get(f"/api/dashboard/teacher/?academic_year_id={archived.id}").status_code == 403
    assert auth_client(admin_user).get(f"/api/dashboard/teacher/?academic_year_id={archived.id}").status_code == 200


@pytest.mark.django_db
def test_external_supervisor_can_access_teacher_dashboard(user_factory):
    year = create_year()
    external = create_teacher(user_factory, "D-EXT", User.BusinessIdentity.EXTERNAL_SUPERVISOR)

    response = auth_client(external).get("/api/dashboard/teacher/")

    assert response.status_code == 200
    assert response.json()["academic_year"]["id"] == year.id


@pytest.mark.django_db
def test_student_dashboard_returns_team_subject_defense_and_latest_deliverables(
    student_user,
    teacher_user,
    user_factory,
):
    year = create_year()
    set_student_year(student_user, year)
    member = create_student(user_factory, "D-STU-MEMBER", year)
    team = create_team(year, "D-STUDENT", Team.Status.VALIDATED, leader=student_user, member=member, supervisor=teacher_user)
    subject = assign_subject(team, teacher_user, "D-STUDENT-SUB")
    defense = create_defense(team, student_user, Defense.Status.SCHEDULED, timezone.now() + timedelta(days=5))
    create_deliverable(team, student_user, name="older.txt")
    latest = create_deliverable(team, member, status=DeliverableFile.ReviewStatus.NEEDS_REVISION, name="latest.txt")

    response = auth_client(student_user).get("/api/dashboard/student/")

    assert response.status_code == 200
    data = response.json()
    assert data["team"]["team_code"] == team.pk
    assert data["team"]["role"] == TeamParticipant.Role.LEADER
    assert {member["role"] for member in data["team"]["members"]} == {TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER}
    assert data["subject"]["id"] == subject.id
    assert data["defense"]["id"] == str(defense.id)
    assert data["assignment"] == {"selection_round": Team.SelectionRound.FIRST, "assigned": True}
    assert data["deliverables"]["total_files"] == 2
    assert data["deliverables"]["latest"][0]["file_id"] == str(latest.id)


@pytest.mark.django_db
def test_student_with_no_team_gets_safe_empty_dashboard(student_user):
    year = create_year()
    set_student_year(student_user, year)

    response = auth_client(student_user).get("/api/dashboard/student/")

    assert response.status_code == 200
    data = response.json()
    assert data["team"] is None
    assert data["subject"] is None
    assert data["defense"] is None
    assert data["deliverables"] == {"total_files": 0, "latest": []}
    assert data["assignment"] == {"selection_round": "", "assigned": False}


@pytest.mark.django_db
def test_student_cannot_access_archived_academic_year_data(student_user):
    archived = create_year("2019/2020", status=AcademicYear.Status.ARCHIVED)
    set_student_year(student_user, archived)

    response = auth_client(student_user).get(f"/api/dashboard/student/?academic_year_id={archived.id}")

    assert response.status_code == 403


@pytest.mark.django_db
def test_dashboards_do_not_mutate_data(admin_user, student_user):
    year = create_year()
    set_student_year(student_user, year)
    create_team(year, "D-READONLY", Team.Status.FORMING)
    before = {
        "teams": Team.objects.count(),
        "subjects": Subject.objects.count(),
        "defenses": Defense.objects.count(),
        "deliverables": DeliverableFile.objects.count(),
        "appeals": Appeal.objects.count(),
    }

    response = auth_client(admin_user).get("/api/dashboard/admin/")

    assert response.status_code == 200
    assert before == {
        "teams": Team.objects.count(),
        "subjects": Subject.objects.count(),
        "defenses": Defense.objects.count(),
        "deliverables": DeliverableFile.objects.count(),
        "appeals": Appeal.objects.count(),
    }
