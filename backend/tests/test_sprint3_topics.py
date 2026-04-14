import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def active_year(db):
    return AcademicYear.objects.create(year="2025/2026", is_active=True, is_archived=False)


@pytest.mark.django_db
def test_teacher_creates_subject_draft(teacher_user, active_year):
    client = auth_client(teacher_user)

    response = client.post(
        "/api/teacher/subjects/",
        {
            "title": "AI for Predictive Maintenance",
            "description": "Build a predictive maintenance prototype.",
            "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
            "technologies": "Python, FastAPI",
            "keywords": "ai,maintenance,prediction",
            "academic_year": active_year.id,
        },
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == Subject.Status.DRAFT
    assert data["title"] == "AI for Predictive Maintenance"
    assert data["academic_year"]["id"] == active_year.id


@pytest.mark.django_db
def test_teacher_cannot_create_subject_in_inactive_year(teacher_user, active_year):
    inactive_year = AcademicYear.objects.create(year="2030/2031", is_active=False, is_archived=False)
    client = auth_client(teacher_user)

    response = client.post(
        "/api/teacher/subjects/",
        {
            "title": "Wrong Year",
            "description": "desc",
            "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
            "academic_year": inactive_year.id,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["academic_year"][0] == "Subject must be linked to the active academic year."


@pytest.mark.django_db
def test_subject_creation_fails_if_no_active_academic_year(teacher_user):
    client = auth_client(teacher_user)

    response = client.post(
        "/api/teacher/subjects/",
        {
            "title": "No Active Year",
            "description": "desc",
            "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["academic_year"][0] == "No active academic year is configured."


@pytest.mark.django_db
def test_teacher_sees_only_own_subjects_in_personal_list(teacher_user, user_factory, active_year):
    other_teacher = user_factory(
        matricule="TEA777",
        email="other-teacher@example.com",
        global_role=User.GlobalRole.TEACHER,
    )

    own_subject = Subject.objects.create(
        title="Own Subject",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )
    Subject.objects.create(
        title="Other Subject",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        proposed_by=other_teacher,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.get("/api/teacher/subjects/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert own_subject.id in ids
    assert len(ids) == 1


@pytest.mark.django_db
def test_teacher_cannot_edit_another_teacher_subject(teacher_user, user_factory, active_year):
    other_teacher = user_factory(
        matricule="TEA778",
        email="teacher-b@example.com",
        global_role=User.GlobalRole.TEACHER,
    )
    subject = Subject.objects.create(
        title="Other Teacher Subject",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        proposed_by=other_teacher,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.patch(
        f"/api/teacher/subjects/{subject.id}/",
        {"title": "Hacked"},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_teacher_can_edit_draft(teacher_user, active_year):
    subject = Subject.objects.create(
        title="Draft Subject",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.patch(
        f"/api/teacher/subjects/{subject.id}/",
        {"title": "Updated Draft Subject"},
        format="json",
    )

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.title == "Updated Draft Subject"


@pytest.mark.django_db
def test_teacher_can_edit_rejected(teacher_user, active_year):
    subject = Subject.objects.create(
        title="Rejected Subject",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.REJECTED,
        rejection_reason="Need clearer scope",
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.patch(
        f"/api/teacher/subjects/{subject.id}/",
        {"description": "updated description"},
        format="json",
    )

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.description == "updated description"


@pytest.mark.django_db
def test_teacher_cannot_edit_submitted(teacher_user, active_year):
    subject = Subject.objects.create(
        title="Submitted Subject",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.patch(
        f"/api/teacher/subjects/{subject.id}/",
        {"title": "not allowed"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["status"][0] == "Only DRAFT or REJECTED subjects can be edited by teacher."


@pytest.mark.django_db
def test_teacher_submits_draft_successfully(teacher_user, active_year):
    subject = Subject.objects.create(
        title="Draft To Submit",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.post(f"/api/teacher/subjects/{subject.id}/submit/", {}, format="json")

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.status == Subject.Status.SUBMITTED
    assert subject.submitted_at is not None


@pytest.mark.django_db
def test_teacher_cannot_resubmit_non_rejected_subject(teacher_user, active_year):
    subject = Subject.objects.create(
        title="Draft",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.post(f"/api/teacher/subjects/{subject.id}/resubmit/", {}, format="json")

    assert response.status_code == 400
    assert response.json()["status"] == "Only REJECTED subject can be resubmitted."


@pytest.mark.django_db
def test_admin_approves_submitted_subject(admin_user, teacher_user, active_year):
    subject = Subject.objects.create(
        title="For Approval",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(admin_user)
    response = client.post(f"/api/admin/subjects/{subject.id}/approve/", {}, format="json")

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.status == Subject.Status.APPROVED
    assert subject.reviewed_by_id == admin_user.id


@pytest.mark.django_db
def test_admin_rejects_submitted_subject_with_reason(admin_user, teacher_user, active_year):
    subject = Subject.objects.create(
        title="For Rejection",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(admin_user)
    response = client.post(
        f"/api/admin/subjects/{subject.id}/reject/",
        {"reason": "Scope is too broad"},
        format="json",
    )

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.status == Subject.Status.REJECTED
    assert subject.rejection_reason == "Scope is too broad"


@pytest.mark.django_db
def test_reject_without_reason_fails(admin_user, teacher_user, active_year):
    subject = Subject.objects.create(
        title="Invalid Reject",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(admin_user)
    response = client.post(
        f"/api/admin/subjects/{subject.id}/reject/",
        {"reason": ""},
        format="json",
    )

    assert response.status_code == 400
    assert "reason" in response.json()


@pytest.mark.django_db
def test_public_catalog_shows_only_approved_subjects(student_user, teacher_user, active_year):
    approved = Subject.objects.create(
        title="Approved",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )
    Subject.objects.create(
        title="Submitted",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(student_user)
    response = client.get("/api/subjects/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert ids == [approved.id]


@pytest.mark.django_db
def test_public_catalog_returns_empty_when_no_active_year(student_user, teacher_user):
    AcademicYear.objects.create(year="2024/2025", is_active=False, is_archived=False)
    archived_year = AcademicYear.objects.create(year="2023/2024", is_active=False, is_archived=False)
    archived_year.is_archived = True
    archived_year.save(update_fields=["is_archived", "updated_at"])

    client = auth_client(student_user)
    response = client.get("/api/subjects/")

    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_public_catalog_excludes_archived_subjects(student_user, teacher_user, active_year):
    Subject.objects.create(
        title="Archived Approved",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.ARCHIVED,
        is_archived=True,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(student_user)
    response = client.get("/api/subjects/")

    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_public_catalog_excludes_non_active_or_archived_academic_year(student_user, teacher_user):
    active_year = AcademicYear.objects.create(year="2025/2026", is_active=True, is_archived=False)
    inactive_year = AcademicYear.objects.create(
        year="2024/2025",
        is_active=False,
        is_archived=False,
    )
    soon_archived_year = AcademicYear.objects.create(
        year="2023/2024",
        is_active=False,
        is_archived=False,
    )

    visible = Subject.objects.create(
        title="Visible",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )
    Subject.objects.create(
        title="Inactive AY",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=inactive_year,
    )
    archived_year_subject = Subject.objects.create(
        title="Archived AY",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=soon_archived_year,
    )
    soon_archived_year.is_archived = True
    soon_archived_year.save(update_fields=["is_archived", "updated_at"])

    client = auth_client(student_user)
    response = client.get("/api/subjects/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert ids == [visible.id]
    assert archived_year_subject.id not in ids


@pytest.mark.django_db
def test_teacher_public_catalog_view_also_shows_only_approved(teacher_user, active_year):
    Subject.objects.create(
        title="Approved",
        description="desc",
        subject_type=Subject.SubjectType.STARTUP_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )
    Subject.objects.create(
        title="Draft",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(teacher_user)
    response = client.get("/api/subjects/")

    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_admin_subject_moderation_list_works(admin_user, teacher_user, active_year):
    target = Subject.objects.create(
        title="Target",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.SUBMITTED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )
    Subject.objects.create(
        title="Other",
        description="desc",
        subject_type=Subject.SubjectType.RESEARCH_PROJECT,
        status=Subject.Status.DRAFT,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(admin_user)
    response = client.get(f"/api/admin/subjects/?status=SUBMITTED&proposed_by={teacher_user.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == target.id


@pytest.mark.django_db
def test_archive_endpoint_works(admin_user, teacher_user, active_year):
    subject = Subject.objects.create(
        title="To Archive",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.APPROVED,
        proposed_by=teacher_user,
        academic_year=active_year,
    )

    client = auth_client(admin_user)
    response = client.post(f"/api/admin/subjects/{subject.id}/archive/", {}, format="json")

    assert response.status_code == 200
    subject.refresh_from_db()
    assert subject.is_archived is True
    assert subject.status == Subject.Status.ARCHIVED
