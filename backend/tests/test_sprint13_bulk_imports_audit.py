from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.academics.models import AcademicYear
from apps.accounts.models import PasswordResetOTP, PlatformAccessGrant, StudentProfile, TeacherProfile, User
from apps.audit.models import AdminActionLog
from apps.imports.models import UserImportBatch



def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def csv_upload(content, name="users.csv"):
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def preview(client, content, import_type=UserImportBatch.ImportType.STUDENTS, name="users.csv"):
    return client.post(
        "/api/admin/imports/users/preview/",
        {"file": csv_upload(content, name=name), "import_type": import_type},
        format="multipart",
    )


@pytest.mark.django_db
def test_admin_can_preview_valid_student_csv(admin_user):
    year = create_year()
    content = "matricule,email,first_name,last_name,moyenne_generale,specialite,academic_year\nS100,s100@example.com,Ada,Lovelace,15.25,SI,2025/2026\n"

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    data = response.json()
    assert data["total_rows"] == 1
    assert data["valid_rows"] == 1
    assert data["invalid_rows"] == 0
    assert UserImportBatch.objects.get(pk=data["id"]).normalized_rows[0]["academic_year_id"] == year.id
    assert AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.USER_IMPORT_PREVIEWED).exists()


@pytest.mark.django_db
def test_admin_can_preview_valid_teacher_csv(admin_user):
    content = "matricule,email,first_name,last_name,grade,departement\nT100,t100@example.com,Alan,Turing,Professor,CS\n"

    response = preview(auth_client(admin_user), content, UserImportBatch.ImportType.TEACHERS)

    assert response.status_code == 201
    assert response.json()["valid_rows"] == 1


@pytest.mark.django_db
def test_student_and_teacher_cannot_preview_import(student_user, teacher_user):
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"

    assert preview(auth_client(student_user), content).status_code == 403
    assert preview(auth_client(teacher_user), content).status_code == 403


@pytest.mark.django_db
def test_preview_does_not_create_users(admin_user):
    create_year()
    before = User.objects.count()
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    assert User.objects.count() == before


@pytest.mark.django_db
def test_preview_reports_missing_required_column(admin_user):
    create_year()
    content = "matricule,email,first_name\nS100,s100@example.com,Ada\n"

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    assert response.json()["invalid_rows"] == 1
    assert any(error["code"] == "MISSING_REQUIRED_COLUMN" for error in response.json()["errors"])


@pytest.mark.django_db
def test_preview_rejects_duplicates_and_existing_users(admin_user, student_user):
    create_year()
    content = (
        "matricule,email,first_name,last_name\n"
        "S100,s100@example.com,Ada,Lovelace\n"
        "S100,s101@example.com,Grace,Hopper\n"
        f"S102,{student_user.email},Existing,Email\n"
        f"{student_user.matricule},s103@example.com,Existing,Matricule\n"
    )

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    codes = {error["code"] for error in response.json()["errors"]}
    assert "DUPLICATE_IN_FILE" in codes
    assert "EXISTS" in codes


@pytest.mark.django_db
def test_preview_validates_student_average_and_academic_year_status(admin_user):
    create_year()
    create_year("2024/2025", AcademicYear.Status.CLOSED)
    content = (
        "matricule,email,first_name,last_name,moyenne_generale,academic_year\n"
        "S100,s100@example.com,Ada,Lovelace,21,2025/2026\n"
        "S101,s101@example.com,Grace,Hopper,12,2024/2025\n"
    )

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    codes = {error["code"] for error in response.json()["errors"]}
    assert "INVALID_AVERAGE" in codes
    assert "NOT_ACTIVE" in codes


@pytest.mark.django_db
def test_missing_academic_year_uses_active_year(admin_user):
    year = create_year()
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"

    response = preview(auth_client(admin_user), content)

    assert response.status_code == 201
    batch = UserImportBatch.objects.get(pk=response.json()["id"])
    assert batch.normalized_rows[0]["academic_year_id"] == year.id


@pytest.mark.django_db
def test_preview_rejects_unsupported_extension_and_empty_file(admin_user):
    client = auth_client(admin_user)
    bad = client.post(
        "/api/admin/imports/users/preview/",
        {"file": csv_upload("hello", name="users.txt"), "import_type": UserImportBatch.ImportType.STUDENTS},
        format="multipart",
    )
    empty = client.post(
        "/api/admin/imports/users/preview/",
        {"file": SimpleUploadedFile("users.csv", b"", content_type="text/csv"), "import_type": UserImportBatch.ImportType.STUDENTS},
        format="multipart",
    )

    assert bad.status_code == 400
    assert empty.status_code == 400


@pytest.mark.django_db
def test_template_endpoints_return_expected_headers(admin_user):
    client = auth_client(admin_user)

    students = client.get("/api/admin/imports/users/template/?import_type=STUDENTS")
    teachers = client.get("/api/admin/imports/users/template/?import_type=TEACHERS")

    assert students.status_code == 200
    assert "matricule,email,first_name,last_name,moyenne_generale,specialite,academic_year" in students.content.decode()
    assert teachers.status_code == 200
    assert "matricule,email,first_name,last_name,grade,departement" in teachers.content.decode()


@pytest.mark.django_db
def test_confirm_requires_confirm_true(admin_user):
    create_year()
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"
    batch_id = preview(auth_client(admin_user), content).json()["id"]

    response = auth_client(admin_user).post("/api/admin/imports/users/confirm/", {"batch_id": batch_id, "confirm": False})

    assert response.status_code == 400


@pytest.mark.django_db
def test_confirm_creates_students_profiles_solo_team_and_hides_password(admin_user):
    create_year()
    content = "matricule,email,first_name,last_name,moyenne_generale,specialite\nS100,s100@example.com,Ada,Lovelace,14.5,SI\n"
    client = auth_client(admin_user)
    batch_id = preview(client, content).json()["id"]

    response = client.post("/api/admin/imports/users/confirm/", {"batch_id": batch_id, "confirm": True})

    assert response.status_code == 200
    data = response.json()
    assert data["created_count"] == 1
    assert "raw_password" not in str(data).lower()
    assert "generated_password" not in str(data).lower()
    user = User.objects.get(matricule="S100")
    assert user.business_identity == User.BusinessIdentity.STUDENT
    assert user.account_status == User.AccountStatus.ACTIVE
    assert user.must_reset_password is True
    assert StudentProfile.objects.filter(user=user, annual_average="14.50", speciality="SI").exists()
    assert user.team_participations.filter(role="LEADER", status="ACTIVE").exists()
    assert AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.USER_IMPORT_COMPLETED).exists()
    assert AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.USER_CREATED_BY_IMPORT, target_id=str(user.id)).exists()


@pytest.mark.django_db
def test_confirm_creates_teachers_and_profiles(admin_user):
    content = "matricule,email,first_name,last_name,grade,departement\nT100,t100@example.com,Alan,Turing,Professor,CS\n"
    client = auth_client(admin_user)
    batch_id = preview(client, content, UserImportBatch.ImportType.TEACHERS).json()["id"]

    response = client.post("/api/admin/imports/users/confirm/", {"batch_id": batch_id, "confirm": True})

    assert response.status_code == 200
    user = User.objects.get(matricule="T100")
    assert user.business_identity == User.BusinessIdentity.TEACHER
    assert user.must_reset_password is True
    assert TeacherProfile.objects.filter(user=user, grade="Professor", department="CS").exists()


@pytest.mark.django_db
def test_confirm_rejects_invalid_batch_by_default_and_allow_partial_creates_valid_rows(admin_user):
    create_year()
    content = (
        "matricule,email,first_name,last_name\n"
        "S100,s100@example.com,Ada,Lovelace\n"
        "S101,not-an-email,Grace,Hopper\n"
    )
    client = auth_client(admin_user)
    batch_id = preview(client, content).json()["id"]

    rejected = client.post("/api/admin/imports/users/confirm/", {"batch_id": batch_id, "confirm": True})
    accepted = client.post(
        "/api/admin/imports/users/confirm/",
        {"batch_id": batch_id, "confirm": True, "allow_partial": True},
    )

    assert rejected.status_code == 400
    assert accepted.status_code == 200
    assert User.objects.filter(matricule="S100").exists()
    assert not User.objects.filter(matricule="S101").exists()
    assert accepted.json()["skipped_count"] == 1


@pytest.mark.django_db
def test_confirm_uses_stored_rows_not_tampered_payload(admin_user):
    create_year()
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"
    client = auth_client(admin_user)
    batch_id = preview(client, content).json()["id"]

    response = client.post(
        "/api/admin/imports/users/confirm/",
        {"batch_id": batch_id, "confirm": True, "rows": [{"matricule": "EVIL"}]},
    )

    assert response.status_code == 200
    assert User.objects.filter(matricule="S100").exists()
    assert not User.objects.filter(matricule="EVIL").exists()


@pytest.mark.django_db
def test_imported_user_login_blocked_until_password_reset(admin_user):
    create_year()
    content = "matricule,email,first_name,last_name\nS100,s100@example.com,Ada,Lovelace\n"
    client = auth_client(admin_user)
    batch_id = preview(client, content).json()["id"]
    client.post("/api/admin/imports/users/confirm/", {"batch_id": batch_id, "confirm": True})
    user = User.objects.get(matricule="S100")
    user.set_password("Knownpass123!")
    user.save(update_fields=["password", "updated_at"])

    blocked = APIClient().post("/api/auth/login/", {"identifier": "S100", "password": "Knownpass123!"})
    otp = PasswordResetOTP.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=10),
        verified_at=timezone.now(),
        verification_token="reset-token",
    )
    otp.set_otp("123456")
    otp.save(update_fields=["otp_code_hash"])
    reset = APIClient().post(
        "/api/auth/password-reset/confirm/",
        {
            "identifier": "S100",
            "verification_token": "reset-token",
            "new_password": "Newpass123!",
            "confirm_password": "Newpass123!",
        },
    )
    user.refresh_from_db()
    login = APIClient().post("/api/auth/login/", {"identifier": "S100", "password": "Newpass123!"})

    assert blocked.status_code == 401
    assert "Password reset required" in str(blocked.json())
    assert reset.status_code == 200
    assert user.must_reset_password is False
    assert login.status_code == 200


@pytest.mark.django_db
def test_super_admin_can_list_logs_and_admin_cannot(admin_user, super_admin_user):
    AdminActionLog.objects.create(
        actor=super_admin_user,
        action_type=AdminActionLog.ActionType.USER_IMPORT_PREVIEWED,
        target_model="imports.UserImportBatch",
        target_id="1",
    )

    forbidden = auth_client(admin_user).get("/api/super-admin/audit/admin-actions/")
    allowed = auth_client(super_admin_user).get("/api/super-admin/audit/admin-actions/")

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["count"] == 1


@pytest.mark.django_db
def test_platform_grant_create_and_revoke_create_admin_logs(super_admin_user, user_factory):
    teacher = user_factory(
        matricule="GRANT-T",
        email="grant-t@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
    )
    client = auth_client(super_admin_user)

    created = client.post(
        "/api/super-admin/platform-access-grants/",
        {"user": teacher.id, "access_level": PlatformAccessGrant.AccessLevel.ADMIN},
    )
    revoked = client.post(f"/api/super-admin/platform-access-grants/{created.json()['id']}/revoke/", {})

    assert created.status_code == 201
    assert revoked.status_code == 200
    assert AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.PLATFORM_GRANT_CREATED).exists()
    assert AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.PLATFORM_GRANT_REVOKED).exists()
