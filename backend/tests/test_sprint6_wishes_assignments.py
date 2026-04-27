from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import StudentProfile, User
from apps.academics.models import AcademicYear
from apps.assignments.models import Appeal, WishItem, WishList
from apps.assignments.services import AppealService, AssignmentService, WishListService
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
    open_campaign_phase(year, CampaignPhase.PhaseType.TEAM_FORMATION, display_order=1)
    open_campaign_phase(year, CampaignPhase.PhaseType.WISHLIST_1, display_order=2)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=3)
    open_campaign_phase(year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS, display_order=4)
    open_campaign_phase(year, CampaignPhase.PhaseType.WISHLIST_2, display_order=5)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_2, display_order=6)
    return year


@pytest.fixture
def student_two(user_factory):
    return user_factory(
        matricule="S6STU002",
        email="s6-student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def student_three(user_factory):
    return user_factory(
        matricule="S6STU003",
        email="s6-student3@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def student_four(user_factory):
    return user_factory(
        matricule="S6STU004",
        email="s6-student4@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def teacher_two(user_factory):
    return user_factory(
        matricule="S6TEA002",
        email="s6-teacher2@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
    )


def approve_subject(teacher, academic_year, index, subject_type=Subject.SubjectType.APPLIED_PROJECT):
    return Subject.objects.create(
        subject_code=f"S6-SUB-{index}",
        title=f"Subject {index}",
        description="Approved subject",
        subject_type=subject_type,
        status=Subject.Status.APPROVED,
        proposed_by=teacher,
        academic_year=academic_year,
    )


def lock_team_for(student, academic_year):
    team = TeamService.create_solo_team_for_student(student, academic_year)
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    return team


def add_active_member(team, student):
    return TeamParticipant.objects.create(
        team=team,
        user=student,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
        joined_at=timezone.now(),
    )


def submit_wishlist(team, actor, subjects, round_value=Team.SelectionRound.FIRST):
    return WishListService.submit_wishlist(
        team,
        actor,
        round_value,
        [{"subject_id": subject.id, "rank": index + 1} for index, subject in enumerate(subjects)],
    )


@pytest.mark.django_db
def test_catalog_shows_all_approved_unassigned_subjects_for_team_size_lte_2(student_user, teacher_user, active_year):
    lock_team_for(student_user, active_year)
    applied = approve_subject(teacher_user, active_year, 1, Subject.SubjectType.APPLIED_PROJECT)
    startup = approve_subject(teacher_user, active_year, 2, Subject.SubjectType.STARTUP_PROJECT)

    response = auth_client(student_user).get("/api/subjects/catalog/")

    assert response.status_code == 200
    subject_ids = {item["id"] for item in response.json()["results"]}
    assert {applied.id, startup.id}.issubset(subject_ids)


@pytest.mark.django_db
def test_catalog_for_team_size_gt_2_shows_only_startup_subjects(
    student_user, student_two, student_three, teacher_user, active_year
):
    team = lock_team_for(student_user, active_year)
    add_active_member(team, student_two)
    add_active_member(team, student_three)
    applied = approve_subject(teacher_user, active_year, 3, Subject.SubjectType.APPLIED_PROJECT)
    startup = approve_subject(teacher_user, active_year, 4, Subject.SubjectType.STARTUP_PROJECT)

    response = auth_client(student_user).get("/api/subjects/catalog/")

    assert response.status_code == 200
    subject_ids = {item["id"] for item in response.json()["results"]}
    assert startup.id in subject_ids
    assert applied.id not in subject_ids


@pytest.mark.django_db
def test_assigned_subjects_are_hidden_from_catalog(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 5)
    AssignmentService.manual_assign(admin_user, team, subject)

    response = auth_client(student_user).get("/api/subjects/catalog/")

    assert response.status_code == 200
    assert subject.id not in {item["id"] for item in response.json()["results"]}


@pytest.mark.django_db
def test_leader_can_submit_first_round_wishlist(student_user, teacher_user, active_year):
    team = lock_team_for(student_user, active_year)
    subjects = [approve_subject(teacher_user, active_year, index) for index in range(10, 13)]

    response = auth_client(student_user).post(
        "/api/wishlists/",
        {
            "selection_round": Team.SelectionRound.FIRST,
            "items": [{"subject_id": subject.id, "rank": index + 1} for index, subject in enumerate(subjects)],
        },
        format="json",
    )

    assert response.status_code == 201
    wishlist = WishList.objects.get(team=team)
    assert wishlist.status == WishList.Status.SUBMITTED
    assert wishlist.items.count() == 3


@pytest.mark.django_db
def test_non_leader_cannot_submit_wishlist(student_user, student_two, teacher_user, active_year):
    team = lock_team_for(student_user, active_year)
    add_active_member(team, student_two)
    subjects = [approve_subject(teacher_user, active_year, index) for index in range(20, 22)]

    response = auth_client(student_two).post(
        "/api/wishlists/",
        {
            "selection_round": Team.SelectionRound.FIRST,
            "items": [{"subject_id": subject.id, "rank": index + 1} for index, subject in enumerate(subjects)],
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_forming_team_can_submit_wishlist_and_is_auto_locked(student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 30)

    response = auth_client(student_user).post(
        "/api/wishlists/",
        {"selection_round": Team.SelectionRound.FIRST, "items": [{"subject_id": subject.id, "rank": 1}]},
        format="json",
    )

    assert response.status_code == 201
    team.refresh_from_db()
    assert team.status == Team.Status.LOCKED


@pytest.mark.django_db
def test_wishlist_must_match_configured_size_when_enough_subjects_exist(student_user, teacher_user, active_year):
    active_year.wishlist_size = 5
    active_year.save(update_fields=["wishlist_size", "updated_at"])
    lock_team_for(student_user, active_year)
    subjects = [approve_subject(teacher_user, active_year, index) for index in range(40, 46)]

    response = auth_client(student_user).post(
        "/api/wishlists/",
        {
            "selection_round": Team.SelectionRound.FIRST,
            "items": [{"subject_id": subject.id, "rank": index + 1} for index, subject in enumerate(subjects[:4])],
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_wishlist_may_be_smaller_when_fewer_compatible_subjects_exist(student_user, teacher_user, active_year):
    active_year.wishlist_size = 5
    active_year.save(update_fields=["wishlist_size", "updated_at"])
    team = lock_team_for(student_user, active_year)
    subjects = [approve_subject(teacher_user, active_year, index) for index in range(50, 53)]

    wishlist = submit_wishlist(team, student_user, subjects)

    assert wishlist.items.count() == 3


@pytest.mark.django_db
def test_duplicate_subject_duplicate_rank_and_non_continuous_ranks_are_rejected(student_user, teacher_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject1 = approve_subject(teacher_user, active_year, 60)
    subject2 = approve_subject(teacher_user, active_year, 61)

    with pytest.raises(Exception):
        WishListService.submit_wishlist(
            team,
            student_user,
            Team.SelectionRound.FIRST,
            [{"subject_id": subject1.id, "rank": 1}, {"subject_id": subject1.id, "rank": 2}],
        )
    with pytest.raises(Exception):
        WishListService.submit_wishlist(
            team,
            student_user,
            Team.SelectionRound.FIRST,
            [{"subject_id": subject1.id, "rank": 1}, {"subject_id": subject2.id, "rank": 1}],
        )
    with pytest.raises(Exception):
        WishListService.submit_wishlist(
            team,
            student_user,
            Team.SelectionRound.FIRST,
            [{"subject_id": subject1.id, "rank": 1}, {"subject_id": subject2.id, "rank": 3}],
        )


@pytest.mark.django_db
def test_incompatible_subject_rejected_for_large_team(
    student_user, student_two, student_three, teacher_user, active_year
):
    team = lock_team_for(student_user, active_year)
    add_active_member(team, student_two)
    add_active_member(team, student_three)
    applied = approve_subject(teacher_user, active_year, 70, Subject.SubjectType.APPLIED_PROJECT)

    with pytest.raises(Exception):
        submit_wishlist(team, student_user, [applied])


@pytest.mark.django_db
def test_team_annual_average_computation_uses_default_for_missing_values(
    student_user, student_two, student_three, active_year
):
    team = lock_team_for(student_user, active_year)
    add_active_member(team, student_two)
    add_active_member(team, student_three)
    StudentProfile.objects.filter(user=student_user).update(annual_average=Decimal("14.00"), academic_year=active_year)
    StudentProfile.objects.filter(user=student_two).update(annual_average=Decimal("16.00"), academic_year=active_year)
    StudentProfile.objects.filter(user=student_three).update(annual_average=None, academic_year=active_year)

    average = AssignmentService.compute_team_average(team)

    assert average == Decimal("13.33333333333333333333333333")


@pytest.mark.django_db
def test_team_with_missing_average_uses_default_and_is_not_skipped(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subjects = [approve_subject(teacher_user, active_year, index) for index in range(80, 82)]
    submit_wishlist(team, student_user, subjects)

    summary = AssignmentService.assign_by_merit(admin_user, Team.SelectionRound.FIRST, seed=1)

    assert summary["assigned_teams"][0]["team_code"] == team.pk
    assert summary["skipped_teams"] == []


@pytest.mark.django_db
def test_merit_assignment_prioritizes_higher_average_for_contested_subject(
    student_user, student_two, teacher_user, admin_user, active_year
):
    team_low = lock_team_for(student_user, active_year)
    team_high = lock_team_for(student_two, active_year)
    StudentProfile.objects.filter(user=student_user).update(annual_average=Decimal("12.00"), academic_year=active_year)
    StudentProfile.objects.filter(user=student_two).update(annual_average=Decimal("18.00"), academic_year=active_year)
    contested = approve_subject(teacher_user, active_year, 90)
    fallback = approve_subject(teacher_user, active_year, 91)
    submit_wishlist(team_low, student_user, [contested, fallback])
    submit_wishlist(team_high, student_two, [contested, fallback])

    summary = AssignmentService.assign_by_merit(admin_user, Team.SelectionRound.FIRST, seed=1)

    team_high.refresh_from_db()
    contested.refresh_from_db()
    assert contested.assigned_to_team_id == team_high.pk
    assert team_high.status == Team.Status.LOCKED
    assert summary["assigned_teams"][0]["team_code"] == team_high.pk


@pytest.mark.django_db
def test_assignment_sets_subject_assigned_and_owner_supervisor(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 100)

    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)

    subject.refresh_from_db()
    team.refresh_from_db()
    assert team.status == Team.Status.VALIDATED
    assert subject.status == Subject.Status.ASSIGNED
    assert TeamParticipant.objects.filter(
        team=team,
        user=teacher_user,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    ).exists()


@pytest.mark.django_db
def test_non_admin_cannot_run_assignment(student_user, teacher_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 110)
    submit_wishlist(team, student_user, [subject])

    response = auth_client(student_user).post(
        "/api/admin/assignments/merit/",
        {"selection_round": Team.SelectionRound.FIRST},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_manual_assignment_rejects_already_assigned_incompatible_and_already_assigned_team(
    student_user, student_two, student_three, student_four, teacher_user, admin_user, active_year
):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 120)
    AssignmentService.manual_assign(admin_user, team, subject)

    other_team = lock_team_for(student_two, active_year)
    with pytest.raises(Exception):
        AssignmentService.manual_assign(admin_user, other_team, subject)

    large_team = lock_team_for(student_three, active_year)
    add_active_member(large_team, student_four)
    extra_student = User.objects.create_user(
        matricule="S6STU005",
        email="s6-student5@example.com",
        password="Testpass123!",
        business_identity=User.BusinessIdentity.STUDENT,
    )
    StudentProfile.objects.create(user=extra_student, academic_year=active_year)
    add_active_member(large_team, extra_student)
    applied = approve_subject(teacher_user, active_year, 121, Subject.SubjectType.APPLIED_PROJECT)
    with pytest.raises(Exception):
        AssignmentService.manual_assign(admin_user, large_team, applied)

    another_subject = approve_subject(teacher_user, active_year, 122)
    with pytest.raises(Exception):
        AssignmentService.manual_assign(admin_user, team, another_subject)


@pytest.mark.django_db
def test_leader_can_submit_appeal_after_first_assignment(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 130)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)

    response = auth_client(student_user).post("/api/appeals/", {"reason": "We prefer another topic."}, format="json")

    assert response.status_code == 201
    assert Appeal.objects.get(team=team).status == Appeal.Status.PENDING


@pytest.mark.django_db
def test_cannot_submit_appeal_before_assignment_or_duplicate(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    response = auth_client(student_user).post("/api/appeals/", {"reason": "Too early."}, format="json")
    assert response.status_code == 400

    subject = approve_subject(teacher_user, active_year, 140)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    AppealService.submit_appeal(team, student_user, "First appeal")
    response = auth_client(student_user).post("/api/appeals/", {"reason": "Again."}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_admin_accepts_appeal_and_releases_subject_for_second_round(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 150)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    appeal = AppealService.submit_appeal(team, student_user, "Second round please")

    response = auth_client(admin_user).post(f"/api/admin/appeals/{appeal.pk}/accept/", {}, format="json")

    assert response.status_code == 200
    team.refresh_from_db()
    subject.refresh_from_db()
    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.ACCEPTED
    assert subject.status == Subject.Status.APPROVED
    assert subject.assigned_to_team_id is None
    assert team.status == Team.Status.LOCKED
    assert team.selection_round == Team.SelectionRound.SECOND


@pytest.mark.django_db
def test_admin_rejects_appeal_and_keeps_assignment(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 160)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    appeal = AppealService.submit_appeal(team, student_user, "Please review")

    response = auth_client(admin_user).post(
        f"/api/admin/appeals/{appeal.pk}/reject/",
        {"admin_comment": "Assignment is valid."},
        format="json",
    )

    assert response.status_code == 200
    team.refresh_from_db()
    subject.refresh_from_db()
    appeal.refresh_from_db()
    assert appeal.status == Appeal.Status.REJECTED
    assert subject.assigned_to_team_id == team.pk
    assert team.status == Team.Status.VALIDATED


@pytest.mark.django_db
def test_second_wishlist_only_after_accepted_appeal(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 170)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    appeal = AppealService.submit_appeal(team, student_user, "Need second round")
    with pytest.raises(Exception):
        submit_wishlist(team, student_user, [subject], round_value=Team.SelectionRound.SECOND)

    AppealService.accept_appeal(appeal, admin_user)
    team.refresh_from_db()
    wishlist = submit_wishlist(team, student_user, [subject], round_value=Team.SelectionRound.SECOND)

    assert wishlist.selection_round == Team.SelectionRound.SECOND


@pytest.mark.django_db
def test_second_round_assignment_works_for_accepted_appeal_team(student_user, teacher_user, admin_user, active_year):
    team = lock_team_for(student_user, active_year)
    subject = approve_subject(teacher_user, active_year, 180)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    appeal = AppealService.submit_appeal(team, student_user, "Try again")
    AppealService.accept_appeal(appeal, admin_user)
    team.refresh_from_db()
    submit_wishlist(team, student_user, [subject], round_value=Team.SelectionRound.SECOND)
    StudentProfile.objects.filter(user=student_user).update(annual_average=Decimal("15.00"), academic_year=active_year)

    summary = AssignmentService.assign_by_merit(admin_user, Team.SelectionRound.SECOND, seed=5)

    subject.refresh_from_db()
    team.refresh_from_db()
    assert summary["assigned_teams"][0]["team_code"] == team.pk
    assert subject.status == Subject.Status.ASSIGNED
    assert team.status == Team.Status.LOCKED
