from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PlatformAccessGrant, User
from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_super_admin_can_grant_platform_admin_to_teacher(super_admin_user, teacher_user):
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": teacher_user.id, "access_level": "ADMIN"},
        format="json",
    )

    assert response.status_code == 201
    grant = PlatformAccessGrant.objects.get(user=teacher_user, revoked_at__isnull=True)
    assert grant.access_level == PlatformAccessGrant.AccessLevel.ADMIN


@pytest.mark.django_db
def test_platform_access_grant_rejects_student(super_admin_user, student_user):
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": student_user.id, "access_level": "ADMIN"},
        format="json",
    )

    assert response.status_code == 400
    assert "Platform access can be granted" in response.json()["user"][0]


@pytest.mark.django_db
def test_admin_cannot_create_platform_access_grants(admin_user, teacher_user):
    client = auth_client(admin_user)

    response = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": teacher_user.id, "access_level": "ADMIN"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_revoke_platform_access_removes_admin_permission(super_admin_user, teacher_user):
    grant = PlatformAccessGrant.objects.create(
        user=teacher_user,
        access_level=PlatformAccessGrant.AccessLevel.ADMIN,
        granted_by=super_admin_user,
    )

    super_client = auth_client(super_admin_user)
    revoke_response = super_client.post(
        f"/api/super-admin/platform-access-grants/{grant.id}/revoke/",
        {},
        format="json",
    )

    assert revoke_response.status_code == 200

    teacher_client = auth_client(teacher_user)
    response = teacher_client.get("/api/admin/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_create_campaign_phase(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    client = auth_client(admin_user)

    start = timezone.now()
    end = start + timedelta(days=10)

    response = client.post(
        "/api/admin/campaign-phases/",
        {
            "academic_year": year.id,
            "phase_type": "CAMPAIGN_SETUP",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "display_order": 1,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["phase_type"] == "CAMPAIGN_SETUP"


@pytest.mark.django_db
def test_campaign_phase_invalid_date_range_rejected(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    client = auth_client(admin_user)

    start = timezone.now()
    end = start - timedelta(days=1)

    response = client.post(
        "/api/admin/campaign-phases/",
        {
            "academic_year": year.id,
            "phase_type": "CAMPAIGN_SETUP",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "display_order": 1,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "end_at" in response.json()


@pytest.mark.django_db
def test_campaign_phase_cannot_use_archived_academic_year(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ARCHIVED)
    client = auth_client(admin_user)

    start = timezone.now()

    response = client.post(
        "/api/admin/campaign-phases/",
        {
            "academic_year": year.id,
            "phase_type": "CAMPAIGN_SETUP",
            "start_at": start.isoformat(),
            "display_order": 1,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "academic_year" in response.json()


@pytest.mark.django_db
def test_campaign_phase_list_excludes_archived_by_default(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    active_phase = CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.CAMPAIGN_SETUP,
        start_at=timezone.now(),
        display_order=1,
        is_archived=False,
    )
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
        start_at=timezone.now(),
        display_order=2,
        is_archived=True,
    )

    client = auth_client(admin_user)
    response = client.get("/api/admin/campaign-phases/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert active_phase.id in ids
    assert len(ids) == 1


@pytest.mark.django_db
def test_campaign_phase_list_include_archived(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.CAMPAIGN_SETUP,
        start_at=timezone.now(),
        display_order=1,
        is_archived=False,
    )
    archived_phase = CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
        start_at=timezone.now(),
        display_order=2,
        is_archived=True,
    )

    client = auth_client(admin_user)
    response = client.get("/api/admin/campaign-phases/?include_archived=true")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert archived_phase.id in ids


@pytest.mark.django_db
def test_subject_supports_assigned_status(teacher_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    subject = Subject.objects.create(
        title="Assigned Topic",
        description="desc",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.ASSIGNED,
        proposed_by=teacher_user,
        academic_year=year,
    )

    assert subject.status == Subject.Status.ASSIGNED


@pytest.mark.django_db
def test_platform_access_grant_rejects_external_supervisor(super_admin_user, user_factory):
    external_user = user_factory(
        matricule="EXT001",
        email="external@example.com",
        business_identity=User.BusinessIdentity.EXTERNAL_SUPERVISOR,
    )
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": external_user.id, "access_level": "ADMIN"},
        format="json",
    )

    assert response.status_code == 400
    assert "Platform access can be granted" in response.json()["user"][0]


@pytest.mark.django_db
def test_platform_access_grant_rejects_suspended_user(super_admin_user, user_factory):
    suspended_teacher = user_factory(
        matricule="TEA_SUSP_1",
        email="suspended-teacher@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
        account_status=User.AccountStatus.SUSPENDED,
    )
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": suspended_teacher.id, "access_level": "ADMIN"},
        format="json",
    )

    assert response.status_code == 400
    assert "Only ACTIVE users can receive platform access." in response.json()["user"][0]


@pytest.mark.django_db
def test_no_platform_grant_no_admin_access(user_factory):
    staff_without_grant = user_factory(
        matricule="LEG001",
        email="legacy-admin@example.com",
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        with_platform_access=False,
    )
    client = auth_client(staff_without_grant)

    response = client.get("/api/admin/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_revoked_grant_disables_admin_access(super_admin_user, user_factory):
    admin_user_no_fallback = user_factory(
        matricule="ADM_REV_1",
        email="revoked-admin@example.com",
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        with_platform_access=False,
    )
    grant = PlatformAccessGrant.objects.create(
        user=admin_user_no_fallback,
        access_level=PlatformAccessGrant.AccessLevel.ADMIN,
        granted_by=super_admin_user,
    )

    super_client = auth_client(super_admin_user)
    revoke_response = super_client.post(
        f"/api/super-admin/platform-access-grants/{grant.id}/revoke/",
        {},
        format="json",
    )
    assert revoke_response.status_code == 200

    admin_client = auth_client(admin_user_no_fallback)
    response = admin_client.get("/api/admin/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_subject_attachment_fields_are_persisted_on_teacher_create(teacher_user, open_campaign_phase):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    open_campaign_phase(year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)
    client = auth_client(teacher_user)

    response = client.post(
        "/api/teacher/subjects/",
        {
            "title": "Attachment Subject",
            "description": "desc",
            "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
            "attachment_key": "subjects/att-1.pdf",
            "attachment_original_name": "att-1.pdf",
            "attachment_mime_type": "application/pdf",
            "attachment_size_bytes": 1024,
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["attachment_key"] == "subjects/att-1.pdf"
    assert payload["attachment_original_name"] == "att-1.pdf"
    assert payload["attachment_mime_type"] == "application/pdf"
    assert payload["attachment_size_bytes"] == 1024


@pytest.mark.django_db
def test_admin_subject_list_exposes_assigned_status(admin_user, teacher_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    assigned_subject = Subject.objects.create(
        title="Assigned Listed",
        description="desc",
        subject_type=Subject.SubjectType.STARTUP_PROJECT,
        status=Subject.Status.ASSIGNED,
        proposed_by=teacher_user,
        academic_year=year,
    )
    client = auth_client(admin_user)

    response = client.get("/api/admin/subjects/?status=ASSIGNED")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["id"] == assigned_subject.id
    assert results[0]["status"] == Subject.Status.ASSIGNED


@pytest.mark.django_db
def test_campaign_phase_unique_phase_type_per_year(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.CAMPAIGN_SETUP,
        start_at=timezone.now(),
        display_order=1,
    )
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/campaign-phases/",
        {
            "academic_year": year.id,
            "phase_type": CampaignPhase.PhaseType.CAMPAIGN_SETUP,
            "start_at": timezone.now().isoformat(),
            "display_order": 2,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "phase_type" in response.json()


@pytest.mark.django_db
def test_campaign_phase_unique_display_order_per_year(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.CAMPAIGN_SETUP,
        start_at=timezone.now(),
        display_order=1,
    )
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/campaign-phases/",
        {
            "academic_year": year.id,
            "phase_type": CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
            "start_at": timezone.now().isoformat(),
            "display_order": 1,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "display_order" in response.json()


@pytest.mark.django_db
def test_campaign_phase_archive_endpoint_sets_logical_archive(admin_user):
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    phase = CampaignPhase.objects.create(
        academic_year=year,
        phase_type=CampaignPhase.PhaseType.CAMPAIGN_SETUP,
        start_at=timezone.now(),
        display_order=1,
    )
    client = auth_client(admin_user)

    response = client.post(f"/api/admin/campaign-phases/{phase.id}/archive/", {}, format="json")
    assert response.status_code == 200

    phase.refresh_from_db()
    assert phase.is_archived is True


@pytest.mark.django_db
def test_openapi_schema_contains_sprint4_endpoints():
    client = APIClient()

    response = client.get("/api/schema/")
    assert response.status_code == 200
    schema_text = response.content.decode()

    assert "/api/admin/campaign-phases/" in schema_text
    assert "/api/super-admin/platform-access-grants/" in schema_text
    assert "/api/admin/subjects/" in schema_text
