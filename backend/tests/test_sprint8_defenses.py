from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.assignments.services import AssignmentService
from apps.campaigns.models import CampaignPhase
from apps.defenses.models import Defense, DefenseAttachedFile, DefenseJuryAssignment, DefenseSupervisorDecision
from apps.deliverables.models import DeliverableFile
from apps.teams.models import TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_upload(name="artifact.pdf", content=b"defense", content_type="application/pdf"):
    return SimpleUploadedFile(name=name, content=content, content_type=content_type)


@pytest.fixture
def active_year(db, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    open_campaign_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION, display_order=2)
    open_campaign_phase(year, CampaignPhase.PhaseType.DEFENSE_WINDOW, display_order=3)
    return year


@pytest.fixture
def student_two(user_factory):
    return user_factory(
        matricule="S8STU002",
        email="s8-student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def teacher_two(user_factory):
    return user_factory(
        matricule="S8TEA002",
        email="s8-teacher2@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
    )


@pytest.fixture
def teacher_three(user_factory):
    return user_factory(
        matricule="S8TEA003",
        email="s8-teacher3@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
    )


@pytest.fixture
def external_supervisor(user_factory):
    return user_factory(
        matricule="S8EXT001",
        email="s8-external@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
    )


def approve_subject(teacher, academic_year, code="S8-SUBJECT"):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Validated team subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher,
        academic_year=academic_year,
    )


def build_validated_team(student, teacher, admin_user, academic_year, code="S8-SUBJECT"):
    team = TeamService.create_solo_team_for_student(student, academic_year)
    team.status = team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    subject = approve_subject(teacher, academic_year, code=code)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    team.refresh_from_db()
    subject.refresh_from_db()
    return team, subject


def create_deliverable(team, uploader, name="existing.pdf"):
    return DeliverableFile.objects.create(
        team=team,
        file=make_upload(name=name),
        original_filename=name,
        file_size=7,
        content_type="application/pdf",
        uploaded_by=uploader,
    )


def add_external_supervisor(team, external_supervisor):
    return TeamParticipant.objects.create(
        team=team,
        user=external_supervisor,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    )


def request_existing_file_defense(user, deliverable):
    return auth_client(user).post(
        "/api/defenses/request/",
        {"existing_file_ids": [str(deliverable.id)]},
        format="json",
    )


def accept_all_supervisors(defense):
    for decision in defense.supervisor_decisions.all():
        auth_client(decision.supervisor).post(f"/api/defenses/{defense.id}/accept/")
    defense.refresh_from_db()
    return defense


def schedule_defense(defense, admin_user, president_user, examiner_users, location="Room A"):
    return auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/schedule/",
        {
            "scheduled_at": (timezone.now() + timedelta(days=7)).isoformat(),
            "location": location,
            "president_user_id": president_user.id,
            "examiner_user_ids": [user.id for user in examiner_users],
        },
        format="json",
    )


@pytest.mark.django_db
def test_leader_can_request_defense_during_defense_window_with_existing_file(
    student_user,
    teacher_user,
    teacher_two,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-1")
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_user, deliverable)

    assert response.status_code == 201
    defense = Defense.objects.get(id=response.json()["id"])
    assert defense.status == Defense.Status.REQUESTED
    assert defense.attached_files.count() == 1
    assert defense.supervisor_decisions.count() == 1


@pytest.mark.django_db
def test_leader_can_request_defense_with_uploaded_pc_file(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-2")

    response = auth_client(student_user).post(
        "/api/defenses/request/",
        {"files": make_upload(name="pc-file.pdf")},
        format="multipart",
    )

    assert response.status_code == 201
    defense = Defense.objects.get(id=response.json()["id"])
    attached = defense.attached_files.select_related("deliverable_file").get()
    assert attached.deliverable_file.team == team
    assert attached.deliverable_file.original_filename == "pc-file.pdf"


@pytest.mark.django_db
def test_request_requires_at_least_one_file(student_user, teacher_user, admin_user, active_year):
    build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-3")

    response = auth_client(student_user).post("/api/defenses/request/", {}, format="json")

    assert response.status_code == 400
    assert "at least one file" in str(response.json()).lower()


@pytest.mark.django_db
def test_non_leader_cannot_request_defense(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-4")
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
    )
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_two, deliverable)

    assert response.status_code == 400
    assert "leader" in str(response.json()).lower()


@pytest.mark.django_db
def test_non_validated_team_cannot_request_defense(student_user, teacher_user, active_year):
    team = TeamService.create_solo_team_for_student(student_user, active_year)
    TeamParticipant.objects.create(
        team=team,
        user=teacher_user,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    )
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_user, deliverable)

    assert response.status_code == 400
    assert "validated" in str(response.json()).lower()


@pytest.mark.django_db
def test_request_requires_defense_window(student_user, teacher_user, admin_user, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year, code="S8-REQ-5")
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_user, deliverable)

    assert response.status_code == 400
    assert "defense window phase" in str(response.json()).lower()


@pytest.mark.django_db
def test_team_without_supervisor_cannot_request_defense(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-6")
    TeamParticipant.objects.filter(
        team=team,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    ).update(status=TeamParticipant.Status.ENDED, ended_at=timezone.now())
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_user, deliverable)

    assert response.status_code == 400
    assert "supervisor" in str(response.json()).lower()


@pytest.mark.django_db
def test_cannot_request_if_active_defense_already_exists(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-7")
    deliverable = create_deliverable(team, student_user)
    first = request_existing_file_defense(student_user, deliverable)

    second = request_existing_file_defense(student_user, deliverable)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "active defense workflow" in str(second.json()).lower()
    assert Defense.objects.filter(team=team).count() == 1


@pytest.mark.django_db
def test_selected_files_must_belong_to_same_team(student_user, student_two, teacher_user, admin_user, active_year):
    team_one, _subject_one = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-8A")
    team_two, _subject_two = build_validated_team(student_two, teacher_user, admin_user, active_year, code="S8-REQ-8B")
    foreign_deliverable = create_deliverable(team_two, student_two, name="foreign.pdf")

    response = request_existing_file_defense(student_user, foreign_deliverable)

    assert response.status_code == 400
    assert "same team" in str(response.json()).lower()
    assert Defense.objects.filter(team=team_one).count() == 0


@pytest.mark.django_db
def test_supervisor_decisions_created_for_all_active_supervisors(
    student_user,
    teacher_user,
    external_supervisor,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-REQ-9")
    add_external_supervisor(team, external_supervisor)
    deliverable = create_deliverable(team, student_user)

    response = request_existing_file_defense(student_user, deliverable)

    defense = Defense.objects.get(id=response.json()["id"])
    assert response.status_code == 201
    assert defense.supervisor_decisions.count() == 2
    assert set(defense.supervisor_decisions.values_list("decision", flat=True)) == {
        DefenseSupervisorDecision.DecisionStatus.PENDING
    }


@pytest.mark.django_db
def test_all_supervisors_must_accept_before_ready_to_schedule(
    student_user,
    teacher_user,
    external_supervisor,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-DEC-1")
    add_external_supervisor(team, external_supervisor)
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])

    first = auth_client(teacher_user).post(f"/api/defenses/{defense.id}/accept/")
    defense.refresh_from_db()
    second = auth_client(external_supervisor).post(f"/api/defenses/{defense.id}/accept/")
    defense.refresh_from_db()

    assert first.status_code == 200
    assert defense.supervisor_decisions.filter(
        supervisor=teacher_user,
        decision=DefenseSupervisorDecision.DecisionStatus.ACCEPTED,
    ).exists()
    assert second.status_code == 200
    assert defense.status == Defense.Status.READY_TO_SCHEDULE


@pytest.mark.django_db
def test_one_denial_cancels_defense(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-DEC-2")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])

    response = auth_client(teacher_user).post(f"/api/defenses/{defense.id}/deny/")
    defense.refresh_from_db()

    assert response.status_code == 200
    assert defense.status == Defense.Status.CANCELLED


@pytest.mark.django_db
def test_non_supervisor_cannot_decide(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-DEC-3")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])

    response = auth_client(student_two).post(f"/api/defenses/{defense.id}/accept/")

    assert response.status_code == 400
    assert "supervisor" in str(response.json()).lower()


@pytest.mark.django_db
def test_cancelled_defense_allows_new_request_later(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-DEC-4")
    deliverable = create_deliverable(team, student_user)
    defense_id = request_existing_file_defense(student_user, deliverable).json()["id"]
    auth_client(teacher_user).post(f"/api/defenses/{defense_id}/deny/")

    response = request_existing_file_defense(student_user, deliverable)

    assert response.status_code == 201
    assert Defense.objects.filter(team=team).count() == 2


@pytest.mark.django_db
def test_admin_can_schedule_after_all_supervisors_accept(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-1")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)

    response = schedule_defense(defense, admin_user, teacher_two, [teacher_three])
    defense.refresh_from_db()

    assert response.status_code == 200
    assert defense.status == Defense.Status.SCHEDULED
    assert defense.jury_assignments.filter(user=teacher_user, role=DefenseJuryAssignment.JuryRole.GUEST).exists()


@pytest.mark.django_db
def test_cannot_schedule_before_all_supervisors_accept(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-2")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])

    response = schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    assert response.status_code == 400
    assert "ready_to_schedule" in str(response.json()).lower()


@pytest.mark.django_db
def test_non_admin_cannot_schedule(student_user, teacher_user, teacher_two, teacher_three, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-3")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)

    response = schedule_defense(defense, teacher_two, teacher_three, [admin_user])

    assert response.status_code == 403


@pytest.mark.django_db
def test_supervisor_cannot_be_president(student_user, teacher_user, teacher_two, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-4")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)

    response = schedule_defense(defense, admin_user, teacher_user, [teacher_two])

    assert response.status_code == 400
    assert "supervisor cannot be president" in str(response.json()).lower()


@pytest.mark.django_db
def test_duplicate_jury_users_rejected(student_user, teacher_user, teacher_two, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-5")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)

    response = schedule_defense(defense, admin_user, teacher_two, [teacher_two])

    assert response.status_code == 400
    assert "duplicate jury users" in str(response.json()).lower()


@pytest.mark.django_db
def test_admin_can_reschedule_scheduled_defense(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-SCH-6")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/reschedule/",
        {"location": "Room B"},
        format="json",
    )
    defense.refresh_from_db()

    assert response.status_code == 200
    assert defense.location == "Room B"


@pytest.mark.django_db
def test_jury_can_view_scheduled_defense(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-JURY-1")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(teacher_two).get(f"/api/jury/defenses/{defense.id}/")

    assert response.status_code == 200
    assert response.json()["status"] == Defense.Status.SCHEDULED


@pytest.mark.django_db
def test_jury_cannot_view_unscheduled_defense(student_user, teacher_user, teacher_two, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-JURY-2")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    DefenseJuryAssignment.objects.create(
        defense=defense,
        user=teacher_two,
        role=DefenseJuryAssignment.JuryRole.EXAMINER,
        assigned_by=admin_user,
    )

    response = auth_client(teacher_two).get(f"/api/jury/defenses/{defense.id}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_attached_files_returned_in_order(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-JURY-3")
    first = create_deliverable(team, student_user, name="first.pdf")
    second = create_deliverable(team, student_user, name="second.pdf")
    defense = Defense.objects.get(
        id=auth_client(student_user)
        .post(
            "/api/defenses/request/",
            {"existing_file_ids": [str(first.id), str(second.id)], "ordering": [str(second.id), str(first.id)]},
            format="json",
        )
        .json()["id"]
    )
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(teacher_two).get(f"/api/jury/defenses/{defense.id}/files/")

    assert response.status_code == 200
    assert [item["order"] for item in response.json()] == [1, 2]
    assert response.json()[0]["deliverable_file"]["original_filename"] == "second.pdf"


@pytest.mark.django_db
def test_admin_can_update_attached_files_before_completion(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-FILES-1")
    original = create_deliverable(team, student_user, name="original.pdf")
    extra = create_deliverable(team, student_user, name="extra.pdf")
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, original).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/files/",
        {
            "existing_file_ids": [str(extra.id)],
            "ordering": [str(extra.id), str(original.id)],
        },
        format="json",
    )
    defense.refresh_from_db()

    assert response.status_code == 200
    assert defense.attached_files.count() == 2
    assert list(defense.attached_files.order_by("order").values_list("deliverable_file__original_filename", flat=True)) == [
        "extra.pdf",
        "original.pdf",
    ]


@pytest.mark.django_db
def test_admin_cannot_remove_last_attached_file(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-FILES-2")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])
    attachment = defense.attached_files.get()

    response = auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/files/",
        {"remove_ids": [str(attachment.id)]},
        format="json",
    )

    assert response.status_code == 400
    assert "at least one attached file" in str(response.json()).lower()


@pytest.mark.django_db
def test_president_can_upload_pv(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-PV-1")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(teacher_two).post(
        f"/api/jury/defenses/{defense.id}/pv/",
        {
            "final_grade": "16.50",
            "deliberation": "Good defense.",
            "pv_file": make_upload(name="pv.pdf"),
        },
        format="multipart",
    )
    defense.refresh_from_db()

    assert response.status_code == 200
    assert defense.status == Defense.Status.COMPLETED
    assert str(defense.final_grade) == "16.50"


@pytest.mark.django_db
def test_admin_can_upload_pv(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-PV-2")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    response = auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/pv/",
        {
            "final_grade": "18.00",
            "deliberation": "Validated by administration.",
            "pv_file": make_upload(name="admin-pv.pdf"),
        },
        format="multipart",
    )

    assert response.status_code == 200
    assert response.json()["status"] == Defense.Status.COMPLETED


@pytest.mark.django_db
@pytest.mark.parametrize("jury_role", [DefenseJuryAssignment.JuryRole.EXAMINER, DefenseJuryAssignment.JuryRole.GUEST])
def test_non_president_non_admin_cannot_upload_pv(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
    jury_role,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code=f"S8-PV-{jury_role}")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])
    actor = teacher_three if jury_role == DefenseJuryAssignment.JuryRole.EXAMINER else teacher_user

    response = auth_client(actor).post(
        f"/api/jury/defenses/{defense.id}/pv/",
        {
            "final_grade": "15.00",
            "deliberation": "Attempted upload.",
            "pv_file": make_upload(name="forbidden.pdf"),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "president" in str(response.json()).lower()


@pytest.mark.django_db
def test_pv_requires_valid_grade_and_required_fields(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-PV-3")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])

    bad_grade = auth_client(teacher_two).post(
        f"/api/jury/defenses/{defense.id}/pv/",
        {
            "final_grade": "21.00",
            "deliberation": "Out of range.",
            "pv_file": make_upload(name="bad-grade.pdf"),
        },
        format="multipart",
    )
    missing_fields = auth_client(teacher_two).post(
        f"/api/jury/defenses/{defense.id}/pv/",
        {"final_grade": "15.00"},
        format="multipart",
    )

    assert bad_grade.status_code == 400
    assert missing_fields.status_code == 400


@pytest.mark.django_db
def test_cannot_modify_files_after_completion(
    student_user,
    teacher_user,
    teacher_two,
    teacher_three,
    admin_user,
    active_year,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S8-PV-4")
    deliverable = create_deliverable(team, student_user)
    defense = Defense.objects.get(id=request_existing_file_defense(student_user, deliverable).json()["id"])
    accept_all_supervisors(defense)
    schedule_defense(defense, admin_user, teacher_two, [teacher_three])
    auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/pv/",
        {
            "final_grade": "17.00",
            "deliberation": "Completed.",
            "pv_file": make_upload(name="completed-pv.pdf"),
        },
        format="multipart",
    )
    extra = create_deliverable(team, student_user, name="late.pdf")

    response = auth_client(admin_user).post(
        f"/api/admin/defenses/{defense.id}/files/",
        {"existing_file_ids": [str(extra.id)]},
        format="json",
    )

    assert response.status_code == 400
    assert "before completion" in str(response.json()).lower()
