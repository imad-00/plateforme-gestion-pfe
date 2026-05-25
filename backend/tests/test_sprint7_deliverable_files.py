import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.assignments.services import AssignmentService
from apps.campaigns.models import CampaignPhase
from apps.deliverables.models import DeliverableFile
from apps.teams.models import Team, TeamParticipant
from apps.teams.services import TeamService
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_upload(name="work.txt", content=b"hello deliverable", content_type="text/plain"):
    return SimpleUploadedFile(name=name, content=content, content_type=content_type)


@pytest.fixture
def active_year(db, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    open_campaign_phase(year, CampaignPhase.PhaseType.WORK_AND_SUPERVISION, display_order=2)
    return year


@pytest.fixture
def student_two(user_factory):
    return user_factory(
        matricule="S7STU002",
        email="s7-student2@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def student_three(user_factory):
    return user_factory(
        matricule="S7STU003",
        email="s7-student3@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
    )


@pytest.fixture
def external_supervisor(user_factory):
    return user_factory(
        matricule="S7EXT001",
        email="s7-external@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
    )


def approve_subject(teacher, academic_year, code="S7-SUBJECT"):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Validated team subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher,
        academic_year=academic_year,
    )


def build_validated_team(student, teacher, admin_user, academic_year, code="S7-SUBJECT"):
    team = TeamService.create_solo_team_for_student(student, academic_year)
    team.status = Team.Status.LOCKED
    team.save(update_fields=["status", "updated_at"])
    subject = approve_subject(teacher, academic_year, code=code)
    AssignmentService.manual_assign(admin_user, team, subject)
    AssignmentService.validate_assignment(admin_user, team)
    team.refresh_from_db()
    subject.refresh_from_db()
    return team, subject


@pytest.mark.django_db
def test_validated_team_member_can_upload_file_during_work_phase(student_user, teacher_user, admin_user, active_year):
    build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-1")

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload(), "comment": "first draft"},
        format="multipart",
    )

    assert response.status_code == 201
    uploaded = DeliverableFile.objects.get(id=response.json()["id"])
    assert uploaded.uploaded_by_id == student_user.id
    assert uploaded.comment == "first draft"
    assert "version_number" not in response.json()


@pytest.mark.django_db
def test_active_leader_can_upload_file(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-2")

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload(name="leader.txt")},
        format="multipart",
    )

    assert response.status_code == 201
    assert DeliverableFile.objects.filter(team=team, uploaded_by=student_user).exists()


@pytest.mark.django_db
def test_active_member_can_upload_file(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-3")
    TeamParticipant.objects.create(
        team=team,
        user=student_two,
        role=TeamParticipant.Role.MEMBER,
        status=TeamParticipant.Status.ACTIVE,
    )

    response = auth_client(student_two).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload(name="member.txt")},
        format="multipart",
    )

    assert response.status_code == 201
    assert DeliverableFile.objects.filter(team=team, uploaded_by=student_two).exists()


@pytest.mark.django_db
def test_team_member_cannot_access_another_teams_file(student_user, student_two, teacher_user, admin_user, active_year):
    team_one, _subject_one = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-4A")
    team_two, _subject_two = build_validated_team(student_two, teacher_user, admin_user, active_year, code="S7-UP-4B")
    deliverable = DeliverableFile.objects.create(
        team=team_one,
        file=make_upload(name="secret.txt"),
        original_filename="secret.txt",
        file_size=12,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(student_two).get(f"/api/deliverable-files/{deliverable.id}/")

    assert response.status_code == 403
    assert DeliverableFile.objects.filter(team=team_two).count() == 0


@pytest.mark.django_db
def test_non_validated_team_cannot_upload(student_user, active_year):
    TeamService.create_solo_team_for_student(student_user, active_year)

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload()},
        format="multipart",
    )

    assert response.status_code == 400
    assert "validated" in str(response.json()).lower()


@pytest.mark.django_db
def test_upload_requires_work_and_supervision_phase(student_user, teacher_user, admin_user, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    build_validated_team(student_user, teacher_user, admin_user, year, code="S7-UP-5")

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload()},
        format="multipart",
    )

    assert response.status_code == 400
    assert "work and supervision phase" in str(response.json()).lower()


@pytest.mark.django_db
def test_upload_stores_original_filename_file_size_and_content_type(student_user, teacher_user, admin_user, active_year):
    build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-6")

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload(name="specification.pdf", content=b"pdf", content_type="application/pdf")},
        format="multipart",
    )

    payload = response.json()
    assert response.status_code == 201
    assert payload["original_filename"] == "specification.pdf"
    assert payload["file_size"] == 3
    assert payload["content_type"] == "application/pdf"


@pytest.mark.django_db
def test_multiple_uploads_are_allowed_freely(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-UP-7")
    client = auth_client(student_user)

    first = client.post("/api/deliverable-files/upload/", {"file": make_upload(name="a.txt")}, format="multipart")
    second = client.post("/api/deliverable-files/upload/", {"file": make_upload(name="b.txt")}, format="multipart")

    assert first.status_code == 201
    assert second.status_code == 201
    assert DeliverableFile.objects.filter(team=team).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "review_status",
    [
        DeliverableFile.ReviewStatus.ACCEPTED,
        DeliverableFile.ReviewStatus.REJECTED,
        DeliverableFile.ReviewStatus.NEEDS_REVISION,
    ],
)
def test_upload_still_allowed_after_any_previous_review_status(
    student_user,
    teacher_user,
    admin_user,
    active_year,
    review_status,
):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code=f"S7-UP-{review_status}")
    first_file = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="first.txt"),
        original_filename="first.txt",
        file_size=5,
        content_type="text/plain",
        uploaded_by=student_user,
        review_status=review_status,
        reviewed_by=teacher_user,
        review_comment="checked",
    )

    response = auth_client(student_user).post(
        "/api/deliverable-files/upload/",
        {"file": make_upload(name="next.txt")},
        format="multipart",
    )

    assert first_file.review_status == review_status
    assert response.status_code == 201
    assert DeliverableFile.objects.filter(team=team).count() == 2


@pytest.mark.django_db
def test_team_member_can_list_own_team_files(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-LIST-1")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="own.txt"),
        original_filename="own.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(student_user).get("/api/deliverable-files/me/")

    assert response.status_code == 200
    assert str(deliverable.id) in {item["id"] for item in response.json()["results"]}


@pytest.mark.django_db
def test_team_member_can_add_flat_comment_visible_in_file_detail(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-COM-1")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="commented.txt"),
        original_filename="commented.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )
    client = auth_client(student_user)

    create_response = client.post(
        f"/api/deliverable-files/{deliverable.id}/comments/",
        {"text": "Please review section 2."},
        format="json",
    )
    detail_response = client.get(f"/api/deliverable-files/{deliverable.id}/")

    assert create_response.status_code == 201
    assert detail_response.status_code == 200
    assert detail_response.json()["comments"][0]["text"] == "Please review section 2."
    assert detail_response.json()["comments"][0]["author"]["id"] == student_user.id


@pytest.mark.django_db
def test_supervisor_can_list_supervised_team_files(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-LIST-2")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="supervised.txt"),
        original_filename="supervised.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(teacher_user).get(f"/api/supervision/teams/{team.pk}/files/")

    assert response.status_code == 200
    assert str(deliverable.id) in {item["id"] for item in response.json()["results"]}


@pytest.mark.django_db
def test_non_supervisor_cannot_list_supervised_endpoint(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-LIST-3")

    response = auth_client(student_two).get(f"/api/supervision/teams/{team.pk}/files/")

    assert response.status_code == 400


@pytest.mark.django_db
def test_internal_teacher_supervisor_can_review_file(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-REV-1")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="review.txt"),
        original_filename="review.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(teacher_user).post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.ACCEPTED, "review_comment": "Good work"},
        format="json",
    )

    assert response.status_code == 200
    deliverable.refresh_from_db()
    assert deliverable.review_status == DeliverableFile.ReviewStatus.ACCEPTED
    assert deliverable.reviewed_by_id == teacher_user.id


@pytest.mark.django_db
def test_supervisor_can_add_comment_to_file(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-COM-2")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="supervisor-note.txt"),
        original_filename="supervisor-note.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(teacher_user).post(
        f"/api/deliverable-files/{deliverable.id}/comments/",
        {"text": "Please expand the methodology chapter."},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["author"]["id"] == teacher_user.id


@pytest.mark.django_db
def test_non_team_non_supervisor_cannot_comment(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-COM-3")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="blocked-comment.txt"),
        original_filename="blocked-comment.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(student_two).post(
        f"/api/deliverable-files/{deliverable.id}/comments/",
        {"text": "I should not see this."},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_comment_requires_work_and_supervision_phase(student_user, teacher_user, admin_user, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year, code="S7-COM-4")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="closed-comment.txt"),
        original_filename="closed-comment.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(student_user).post(
        f"/api/deliverable-files/{deliverable.id}/comments/",
        {"text": "This should wait."},
        format="json",
    )

    assert response.status_code == 400
    assert "work and supervision phase" in str(response.json()).lower()


@pytest.mark.django_db
def test_external_supervisor_can_review_file(student_user, teacher_user, external_supervisor, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-REV-2")
    TeamParticipant.objects.create(
        team=team,
        user=external_supervisor,
        role=TeamParticipant.Role.SUPERVISOR,
        status=TeamParticipant.Status.ACTIVE,
    )
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="external.txt"),
        original_filename="external.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(external_supervisor).post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.NEEDS_REVISION, "review_comment": "Please revise"},
        format="json",
    )

    assert response.status_code == 200
    deliverable.refresh_from_db()
    assert deliverable.review_status == DeliverableFile.ReviewStatus.NEEDS_REVISION
    assert deliverable.reviewed_by_id == external_supervisor.id


@pytest.mark.django_db
def test_non_supervisor_cannot_review_file(student_user, student_two, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-REV-3")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="blocked.txt"),
        original_filename="blocked.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(student_two).post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.REJECTED},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_review_requires_work_and_supervision_phase(student_user, teacher_user, admin_user, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1, display_order=1)
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, year, code="S7-REV-4")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="closed.txt"),
        original_filename="closed.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(teacher_user).post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.ACCEPTED},
        format="json",
    )

    assert response.status_code == 400
    assert "work and supervision phase" in str(response.json()).lower()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "review_status",
    [
        DeliverableFile.ReviewStatus.ACCEPTED,
        DeliverableFile.ReviewStatus.NEEDS_REVISION,
        DeliverableFile.ReviewStatus.REJECTED,
    ],
)
def test_review_can_set_each_supported_status(student_user, teacher_user, admin_user, active_year, review_status):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code=f"S7-REV-{review_status}")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="status.txt"),
        original_filename="status.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(teacher_user).post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": review_status, "review_comment": review_status},
        format="json",
    )

    assert response.status_code == 200
    deliverable.refresh_from_db()
    assert deliverable.review_status == review_status


@pytest.mark.django_db
def test_review_can_be_redone_and_fields_are_overwritten(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-REV-5")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="redo.txt"),
        original_filename="redo.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )
    client = auth_client(teacher_user)

    first = client.post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.NEEDS_REVISION, "review_comment": "Fix layout"},
        format="json",
    )
    second = client.post(
        f"/api/deliverable-files/{deliverable.id}/review/",
        {"review_status": DeliverableFile.ReviewStatus.ACCEPTED, "review_comment": "Looks good now"},
        format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    deliverable.refresh_from_db()
    assert deliverable.review_status == DeliverableFile.ReviewStatus.ACCEPTED
    assert deliverable.review_comment == "Looks good now"
    assert deliverable.reviewed_by_id == teacher_user.id
    assert deliverable.reviewed_at is not None


@pytest.mark.django_db
def test_supervisor_can_list_supervised_teams(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-SUP-1")

    response = auth_client(teacher_user).get("/api/supervision/teams/")

    assert response.status_code == 200
    assert team.pk in {item["team_code"] for item in response.json()["results"]}


@pytest.mark.django_db
def test_admin_cannot_access_deliverable_file_detail_for_monitoring(student_user, teacher_user, admin_user, active_year):
    team, _subject = build_validated_team(student_user, teacher_user, admin_user, active_year, code="S7-ADM-1")
    deliverable = DeliverableFile.objects.create(
        team=team,
        file=make_upload(name="private.txt"),
        original_filename="private.txt",
        file_size=3,
        content_type="text/plain",
        uploaded_by=student_user,
    )

    response = auth_client(admin_user).get(f"/api/deliverable-files/{deliverable.id}/")

    assert response.status_code == 403
