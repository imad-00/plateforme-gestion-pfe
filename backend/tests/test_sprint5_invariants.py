import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService


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
        matricule="INVSTU002",
        email="inv-student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def student_three(user_factory):
    return user_factory(
        matricule="INVSTU003",
        email="inv-student3@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.mark.django_db
def test_double_accept_same_invitation_second_call_fails(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamService.create_solo_team_for_student(student_two, active_year)
    invitation = TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    client = auth_client(student_two)

    first = client.post(f"/api/team-invitations/{invitation.pk}/accept/", {}, format="json")
    second = client.post(f"/api/team-invitations/{invitation.pk}/accept/", {}, format="json")

    assert first.status_code == 200
    assert second.status_code == 400
    assert TeamParticipant.objects.filter(
        user=student_two,
        status=TeamParticipant.Status.ACTIVE,
        role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
    ).exclude(team__status__in=[Team.Status.DISSOLVED, Team.Status.ARCHIVED]).count() == 1


@pytest.mark.django_db
def test_admin_remove_leader_without_replacement_fails(admin_user, student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(admin_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_user.id},
        format="json",
    )

    assert response.status_code == 400
    team.refresh_from_db()
    assert team.status == Team.Status.FORMING
    assert TeamService.count_active_leaders(team) == 1


@pytest.mark.django_db
def test_team_with_only_supervisors_is_dissolved_when_last_student_removed(admin_user, student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=teacher_user,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(admin_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_user.id, "dissolve_if_needed": True},
        format="json",
    )

    assert response.status_code == 200
    team.refresh_from_db()
    assert team.status == Team.Status.DISSOLVED


@pytest.mark.django_db
def test_student_cannot_leave_locked_team(student_user, student_two, active_year):
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
    client = auth_client(student_two)

    response = client.post("/api/teams/leave/", {}, format="json")

    assert response.status_code == 400
    assert TeamParticipant.objects.get(team=team, user=student_two).status == TeamParticipant.Status.ACTIVE


@pytest.mark.django_db
def test_removed_student_always_gets_solo_team(admin_user, student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    client = auth_client(admin_user)

    response = client.post(
        f"/api/admin/teams/{team.pk}/remove-member/",
        {"student_id": student_two.id},
        format="json",
    )

    assert response.status_code == 200
    solo = TeamService.get_active_student_participation(student_two)
    assert solo is not None
    assert solo.role == TeamParticipant.Role.LEADER
    assert solo.team_id != team.pk


@pytest.mark.django_db
def test_duplicate_supervisor_add_is_idempotent(admin_user, student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    client = auth_client(admin_user)

    first = client.post(f"/api/admin/teams/{team.pk}/supervisors/", {"user_id": teacher_user.id}, format="json")
    second = client.post(f"/api/admin/teams/{team.pk}/supervisors/", {"user_id": teacher_user.id}, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    assert TeamParticipant.objects.filter(
        team=team,
        user=teacher_user,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    ).count() == 1


@pytest.mark.django_db
def test_cannot_accept_invitation_if_already_in_active_non_solo_team(student_user, student_two, student_three, active_year):
    team_a = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team_a,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    team_b = TeamService.create_solo_team_for_student(student_three, active_year)
    invitation = TeamParticipant.objects.create(
        team=team_b,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    client = auth_client(student_two)

    response = client.post(f"/api/team-invitations/{invitation.pk}/accept/", {}, format="json")

    assert response.status_code == 400
    invitation.refresh_from_db()
    assert invitation.status == TeamParticipant.Status.PENDING


@pytest.mark.django_db
def test_cannot_accept_invitation_into_locked_team(student_user, student_two, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    invitation = TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.PENDING,
    )
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    client = auth_client(student_two)

    response = client.post(f"/api/team-invitations/{invitation.pk}/accept/", {}, format="json")

    assert response.status_code == 400
    invitation.refresh_from_db()
    assert invitation.status == TeamParticipant.Status.PENDING
