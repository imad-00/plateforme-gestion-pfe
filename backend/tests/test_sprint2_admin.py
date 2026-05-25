import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PlatformAccessGrant, StudentProfile, TeacherProfile, User
from apps.academics.models import AcademicYear


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_admin_can_access_admin_endpoints(admin_user):
    client = auth_client(admin_user)

    response = client.get("/api/admin/users/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_student_forbidden_from_admin_endpoints(student_user):
    client = auth_client(student_user)

    response = client.get("/api/admin/users/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_super_admin_can_create_admin_account(super_admin_user):
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/super-admin/admins/",
        {
            "matricule": "ADM200",
            "email": "newadmin@example.com",
            "first_name": "New",
            "last_name": "Admin",
            "password": "StrongPass123!",
            "access_level": "ADMIN",
        },
        format="json",
    )

    assert response.status_code == 201
    created = User.objects.get(email="newadmin@example.com")
    assert created.business_identity == User.BusinessIdentity.ADMINISTRATIVE_STAFF
    assert PlatformAccessGrant.objects.filter(
        user=created,
        access_level=PlatformAccessGrant.AccessLevel.ADMIN,
        revoked_at__isnull=True,
    ).exists()


@pytest.mark.django_db
def test_admin_cannot_create_super_admin(admin_user):
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "SADM200",
            "email": "newsuper@example.com",
            "first_name": "New",
            "last_name": "Super",
            "password": "StrongPass123!",
            "business_identity": "ADMINISTRATIVE_STAFF",
        },
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["business_identity"][0]
        == "ADMIN can only create/update STUDENT or TEACHER accounts."
    )


@pytest.mark.django_db
def test_academic_year_creation_valid(super_admin_user):
    client = auth_client(super_admin_user)

    response = client.post(
        "/api/admin/academic-years/",
        {"year": "2025/2026", "status": "ACTIVE"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["year"] == "2025/2026"


@pytest.mark.django_db
def test_academic_year_unique_active_constraint_no_auto_switch(super_admin_user):
    client = auth_client(super_admin_user)

    first = AcademicYear.objects.create(year="2024/2025", status=AcademicYear.Status.ACTIVE)
    response = client.post(
        "/api/admin/academic-years/",
        {"year": "2025/2026", "status": "ACTIVE"},
        format="json",
    )

    assert response.status_code == 400
    first.refresh_from_db()
    assert first.status == AcademicYear.Status.ACTIVE
    assert not AcademicYear.objects.filter(year="2025/2026").exists()


@pytest.mark.django_db
def test_archived_academic_year_cannot_be_reactivated(admin_user):
    client = auth_client(admin_user)
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ARCHIVED)

    response = client.patch(
        f"/api/admin/academic-years/{year.id}/",
        {"status": "ACTIVE"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only ACTIVE academic years can be updated through the normal admin endpoint."


@pytest.mark.django_db
def test_archived_academic_year_excluded_from_default_list(admin_user):
    client = auth_client(admin_user)
    AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.CLOSED)
    AcademicYear.objects.create(year="2024/2025", status=AcademicYear.Status.ARCHIVED)

    response = client.get("/api/admin/academic-years/")

    assert response.status_code == 200
    payload = response.json()
    years = [item["year"] for item in payload["results"]]
    assert "2025/2026" in years
    assert "2024/2025" not in years


@pytest.mark.django_db
def test_include_archived_true_returns_archived_years(admin_user):
    client = auth_client(admin_user)
    AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.CLOSED)
    AcademicYear.objects.create(year="2024/2025", status=AcademicYear.Status.ARCHIVED)

    response = client.get("/api/admin/academic-years/?include_archived=true")

    assert response.status_code == 200
    payload = response.json()
    years = [item["year"] for item in payload["results"]]
    assert "2025/2026" in years
    assert "2024/2025" in years


@pytest.mark.django_db
def test_patching_archived_academic_year_is_rejected(admin_user):
    client = auth_client(admin_user)
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ARCHIVED)

    response = client.patch(
        f"/api/admin/academic-years/{year.id}/",
        {"year": "2025/2026-updated"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only ACTIVE academic years can be updated through the normal admin endpoint."


@pytest.mark.django_db
def test_academic_year_archive_endpoint_requires_super_admin_and_closed_year(super_admin_user):
    client = auth_client(super_admin_user)
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.CLOSED)

    response = client.post(
        f"/api/admin/academic-years/{year.id}/archive/",
        {"reason": "Historical archive", "confirm": True},
        format="json",
    )

    assert response.status_code == 200
    year.refresh_from_db()
    assert year.status == AcademicYear.Status.ARCHIVED


@pytest.mark.django_db
def test_user_archive_endpoint(admin_user, student_user):
    client = auth_client(admin_user)

    response = client.post(f"/api/admin/users/{student_user.id}/archive/", {}, format="json")

    assert response.status_code == 200
    student_user.refresh_from_db()
    assert student_user.account_status == User.AccountStatus.ARCHIVED


@pytest.mark.django_db
def test_student_profile_can_link_to_academic_year(admin_user, student_user):
    client = auth_client(admin_user)
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)

    response = client.patch(
        f"/api/admin/users/{student_user.id}/",
        {
            "business_identity": "STUDENT",
            "student_profile": {"academic_year": year.id, "specialite": "AI"},
        },
        format="json",
    )

    assert response.status_code == 200
    student_profile = StudentProfile.objects.get(user=student_user)
    assert student_profile.academic_year_id == year.id
    assert student_profile.specialite == "AI"


@pytest.mark.django_db
def test_user_creation_student_role_creates_or_updates_student_profile(admin_user):
    client = auth_client(admin_user)
    year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "STU999",
            "email": "student999@example.com",
            "first_name": "Stu",
            "last_name": "Dent",
            "password": "StrongPass123!",
            "business_identity": "STUDENT",
            "student_profile": {
                "academic_year": year.id,
                "moyenne_generale": "14.50",
                "specialite": "SE",
            },
        },
        format="json",
    )

    assert response.status_code == 201
    created = User.objects.get(email="student999@example.com")
    profile = StudentProfile.objects.get(user=created)
    assert profile.academic_year_id == year.id
    assert str(profile.moyenne_generale) == "14.50"


@pytest.mark.django_db
def test_student_creation_fails_without_active_academic_year(admin_user):
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "STU_NO_ACTIVE",
            "email": "stu-no-active@example.com",
            "first_name": "Stu",
            "last_name": "NoActive",
            "password": "StrongPass123!",
            "business_identity": "STUDENT",
            "student_profile": {"specialite": "SE"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["student_profile"][0] == "No active academic year is configured."


@pytest.mark.django_db
def test_student_creation_cannot_use_inactive_academic_year(admin_user):
    client = auth_client(admin_user)
    active_year = AcademicYear.objects.create(year="2025/2026", status=AcademicYear.Status.ACTIVE)
    inactive_year = AcademicYear.objects.create(year="2024/2025", status=AcademicYear.Status.CLOSED)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "STU_WRONG_YEAR",
            "email": "stu-wrong-year@example.com",
            "first_name": "Stu",
            "last_name": "WrongYear",
            "password": "StrongPass123!",
            "business_identity": "STUDENT",
            "student_profile": {"academic_year": inactive_year.id, "specialite": "SE"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["student_profile"]["academic_year"][0]
        == "Student profile must be linked to the active academic year."
    )
    assert AcademicYear.objects.get(pk=active_year.id).status == AcademicYear.Status.ACTIVE


@pytest.mark.django_db
def test_user_creation_teacher_role_creates_or_updates_teacher_profile(admin_user):
    client = auth_client(admin_user)

    response = client.post(
        "/api/admin/users/",
        {
            "matricule": "TEA999",
            "email": "teacher999@example.com",
            "first_name": "Tea",
            "last_name": "Cher",
            "password": "StrongPass123!",
            "business_identity": "TEACHER",
            "teacher_profile": {"grade": "MC", "departement": "Informatique"},
        },
        format="json",
    )

    assert response.status_code == 201
    created = User.objects.get(email="teacher999@example.com")
    profile = TeacherProfile.objects.get(user=created)
    assert profile.grade == "MC"


@pytest.mark.django_db
def test_admin_cannot_patch_user_to_admin(admin_user, student_user):
    client = auth_client(admin_user)

    response = client.patch(
        f"/api/admin/users/{student_user.id}/",
        {"business_identity": "ADMINISTRATIVE_STAFF"},
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["business_identity"][0]
        == "ADMIN can only create/update STUDENT or TEACHER accounts."
    )


@pytest.mark.django_db
def test_admin_cannot_patch_user_to_super_admin(admin_user, teacher_user):
    client = auth_client(admin_user)

    response = client.patch(
        f"/api/admin/users/{teacher_user.id}/",
        {"business_identity": "ADMINISTRATIVE_STAFF"},
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["business_identity"][0]
        == "ADMIN can only create/update STUDENT or TEACHER accounts."
    )


@pytest.mark.django_db
def test_admin_list_endpoints_are_paginated(admin_user):
    client = auth_client(admin_user)

    for idx in range(15):
        User.objects.create_user(
            matricule=f"STU-P-{idx}",
            email=f"stu-p-{idx}@example.com",
            password="Testpass123!",
            business_identity=User.BusinessIdentity.STUDENT,
        )

    users_response = client.get("/api/admin/users/")
    years_response = client.get("/api/admin/academic-years/")

    assert users_response.status_code == 200
    assert "count" in users_response.json()
    assert "results" in users_response.json()

    assert years_response.status_code == 200
    assert "count" in years_response.json()
    assert "results" in years_response.json()
