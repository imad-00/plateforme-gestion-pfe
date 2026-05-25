import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PlatformAccessGrant, User
from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def active_year(db, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION)
    return year


@pytest.fixture
def student_two(user_factory):
    return user_factory(
        matricule="STU002",
        email="student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
        first_name="Student",
        last_name="Two",
    )


@pytest.fixture
def external_supervisor(user_factory):
    return user_factory(
        matricule="EXTSUP001",
        email="external-supervisor@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
        first_name="External",
        last_name="Supervisor",
    )


@pytest.mark.django_db
def test_admin_student_creation_creates_solo_team(admin_user, active_year):
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "STU_SOLO_1",
            "email": "solo1@example.com",
            "password": "Testpass123!",
            "business_identity": User.BusinessIdentity.STUDENT,
            "student_profile": {"speciality": "SI"},
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(matricule="STU_SOLO_1")
    participation = TeamService.get_active_student_participation(user)
    assert participation is not None
    assert participation.role == TeamParticipant.Role.LEADER
    assert participation.team.status == Team.Status.FORMING
    assert participation.team.academic_year_id == active_year.id


@pytest.mark.django_db
def test_get_my_team_creates_solo_team(student_user, active_year):
    client = auth_client(student_user)

    response = client.get("/api/teams/me/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == Team.Status.FORMING
    assert payload["active_leader"]["user"]["id"] == student_user.id


@pytest.mark.django_db
def test_leader_can_invite_student_to_forming_team(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamService.create_solo_team_for_student(student_two, active_year)
    client = auth_client(student_user)

    response = client.post(
        f"/api/teams/{team.pk}/invite/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 201
    invitation = TeamParticipant.objects.get(team=team, user=student_two, status=TeamParticipant.Status.PENDING)
    assert invitation.role == TeamParticipant.Role.MEMBER


@pytest.mark.django_db
def test_non_leader_cannot_invite(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(student_two)

    response = client.post(
        f"/api/teams/{team.pk}/invite/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_invite_to_locked_team(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    client = auth_client(student_user)

    response = client.post(
        f"/api/teams/{team.pk}/invite/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_invite_non_student(student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(student_user)

    response = client.post(
        f"/api/teams/{team.pk}/invite/",
        {"student_id": teacher_user.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_invited_student_accepts_and_previous_solo_team_is_dissolved(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    old_solo = TeamService.create_solo_team_for_student(student_two, active_year)
    invitation = TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    client = auth_client(student_two)

    response = client.post(f"/api/team-invitations/{invitation.pk}/accept/", {}, format="json")

    assert response.status_code == 200
    invitation.refresh_from_db()
    old_solo.refresh_from_db()
    assert invitation.status == TeamParticipant.Status.ACTIVE
    assert invitation.joined_at is not None
    assert old_solo.status == Team.Status.DISSOLVED


@pytest.mark.django_db
def test_invitation_reject(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    invitation = TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    client = auth_client(student_two)

    response = client.post(f"/api/team-invitations/{invitation.pk}/reject/", {}, format="json")

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.status == TeamParticipant.Status.REJECTED
    assert invitation.ended_at is not None


@pytest.mark.django_db
def test_member_can_leave_forming_team_and_gets_new_solo(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(student_two)

    response = client.post("/api/teams/leave/", {}, format="json")

    assert response.status_code == 200
    new_participation = TeamService.get_active_student_participation(student_two)
    assert new_participation.team_id != team.pk
    assert new_participation.role == TeamParticipant.Role.LEADER


@pytest.mark.django_db
def test_leader_cannot_leave_normally(student_user, active_year):
    TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(student_user)

    response = client.post("/api/teams/leave/", {}, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_transfer_leadership_in_forming_team(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(student_user)

    response = client.post(
        f"/api/teams/{team.pk}/transfer-leadership/",
        {"new_leader_id": student_two.id},
        format="json",
    )

    assert response.status_code == 200
    assert TeamParticipant.objects.get(team=team, user=student_two).role == TeamParticipant.Role.LEADER
    assert TeamParticipant.objects.get(team=team, user=student_user).role == TeamParticipant.Role.MEMBER


@pytest.mark.django_db
def test_cannot_transfer_to_pending_member(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    client = auth_client(student_user)

    response = client.post(
        f"/api/teams/{team.pk}/transfer-leadership/",
        {"new_leader_id": student_two.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_leader_can_lock_forming_team(student_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(student_user)

    response = client.post(f"/api/teams/{team.pk}/lock/", {}, format="json")

    assert response.status_code == 200
    team.refresh_from_db()
    assert team.status == Team.Status.LOCKED


@pytest.mark.django_db
def test_team_size_limit_blocks_lock(student_user, user_factory, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    for index in range(7):
        member = user_factory(
            matricule=f"SIZE{index}",
            email=f"size{index}@example.com",
            business_identity=User.BusinessIdentity.STUDENT,
        )
        TeamParticipant.objects.create(
            team=team,
            user=member,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.ACTIVE,
            joined_at=timezone.now(),
        )
    client = auth_client(student_user)

    response = client.post(f"/api/teams/{team.pk}/lock/", {}, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_admin_can_add_teacher_and_external_supervisor(admin_user, student_user, teacher_user, external_supervisor, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(admin_user)

    teacher_response = client.post(
        f"/api/admin/teams/{team.pk}/supervisors/",
        {"user_id": teacher_user.id},
        format="json",
    )
    external_response = client.post(
        f"/api/admin/teams/{team.pk}/supervisors/",
        {"user_id": external_supervisor.id},
        format="json",
    )

    assert teacher_response.status_code == 201
    assert external_response.status_code == 201
    assert TeamParticipant.objects.filter(team=team, role=TeamParticipant.Role.SUPERVISOR, status=TeamParticipant.Status.ACTIVE).count() == 2


@pytest.mark.django_db
def test_student_leader_cannot_add_supervisor(student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(student_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/supervisors/",
        {"user_id": teacher_user.id},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_cannot_add_student_as_supervisor(admin_user, student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(admin_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/supervisors/",
        {"user_id": student_two.id},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_admin_can_remove_member_from_locked_team(admin_user, student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    client = auth_client(admin_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 200
    assert TeamService.get_active_student_participation(student_two).team_id != team.pk


@pytest.mark.django_db
def test_admin_removing_leader_requires_new_leader_or_dissolution(admin_user, student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(admin_user)

    missing_new_leader = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_user.id},
        format="json",
    )
    with_new_leader = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_user.id, "new_leader_id": student_two.id},
        format="json",
    )

    assert missing_new_leader.status_code == 400
    assert with_new_leader.status_code == 200
    assert TeamParticipant.objects.get(team=team, user=student_two).role == TeamParticipant.Role.LEADER


@pytest.mark.django_db
def test_subject_owner_supervisor_helper_is_idempotent(student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    subject = Subject.objects.create(
        subject_code="SUB-SUP-1",
        title="Topic",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    first = TeamService.ensure_subject_owner_supervisor(team, subject)
    second = TeamService.ensure_subject_owner_supervisor(team, subject)

    assert first.pk == second.pk
    assert TeamParticipant.objects.filter(team=team, user=teacher_user, role=TeamParticipant.Role.SUPERVISOR).count() == 1


@pytest.mark.django_db
def test_openapi_schema_contains_sprint5_team_endpoints():
    client = APIClient()

    response = client.get("/api/schema/")

    assert response.status_code == 200
    schema_text = response.content.decode()
    assert "/api/teams/me/" in schema_text
    assert "/api/admin/teams/" in schema_text
