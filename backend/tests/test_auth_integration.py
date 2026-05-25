import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import PasswordResetOTP, User


@pytest.mark.django_db
def test_login_with_matricule_valid(student_user):
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.matricule, "password": "Testpass123!"},
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert data["user"]["matricule"] == student_user.matricule


@pytest.mark.django_db
def test_login_with_email_valid(teacher_user):
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"identifier": teacher_user.email, "password": "Testpass123!"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.json()


@pytest.mark.django_db
def test_login_invalid_credentials(student_user):
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_login_archived_user_refused(user_factory):
    archived_user = user_factory(
        matricule="ARCH001",
        email="archived@example.com",
        account_status=User.AccountStatus.ARCHIVED,
    )
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"identifier": archived_user.email, "password": "Testpass123!"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "This account is archived."


@pytest.mark.django_db
def test_login_inactive_user_refused(user_factory):
    inactive_user = user_factory(
        matricule="INACT001",
        email="inactive@example.com",
        account_status=User.AccountStatus.SUSPENDED,
    )
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"identifier": inactive_user.email, "password": "Testpass123!"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "This account is inactive."


@pytest.mark.django_db
def test_refresh_token_valid(student_user):
    client = APIClient()

    login_response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "Testpass123!"},
        format="json",
    )
    refresh = login_response.json()["refresh"]

    response = client.post(
        "/api/auth/refresh/",
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.json()


@pytest.mark.django_db
def test_me_with_valid_token(student_user):
    client = APIClient()

    login_response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "Testpass123!"},
        format="json",
    )
    access = login_response.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me_response = client.get("/api/auth/me/")

    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == student_user.email
    assert me_data["student_profile"] is not None
    assert me_data["teacher_profile"] is None


@pytest.mark.django_db
def test_me_without_token_unauthorized(student_user):
    client = APIClient()

    response = client.get("/api/auth/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_archived_user_forbidden(user_factory):
    client = APIClient()

    archived_user = user_factory(
        matricule="ARCH002",
        email="archived2@example.com",
        account_status=User.AccountStatus.ARCHIVED,
    )
    access = str(RefreshToken.for_user(archived_user).access_token)

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/auth/me/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_change_password_in_session(student_user):
    client = APIClient()
    login_response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "Testpass123!"},
        format="json",
    )
    access = login_response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/auth/change-password/",
        {
            "old_password": "Testpass123!",
            "new_password": "NewStrongPass123!",
            "confirm_password": "NewStrongPass123!",
        },
        format="json",
    )
    assert response.status_code == 200

    relogin = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "NewStrongPass123!"},
        format="json",
    )
    assert relogin.status_code == 200


@pytest.mark.django_db
def test_password_reset_flow_with_otp(student_user):
    client = APIClient()

    request_otp = client.post(
        "/api/auth/password-reset/request-otp/",
        {"identifier": student_user.email},
        format="json",
    )
    assert request_otp.status_code == 200

    otp_record = PasswordResetOTP.objects.filter(user=student_user).order_by("-created_at").first()
    assert otp_record is not None
    otp_record.set_otp("123456")
    otp_record.save(update_fields=["otp_code_hash", "updated_at"])

    verify = client.post(
        "/api/auth/password-reset/verify-otp/",
        {"identifier": student_user.email, "otp": "123456"},
        format="json",
    )
    assert verify.status_code == 200
    verification_token = verify.json()["verification_token"]

    confirm = client.post(
        "/api/auth/password-reset/confirm/",
        {
            "identifier": student_user.email,
            "verification_token": verification_token,
            "new_password": "ResetPass123!",
            "confirm_password": "ResetPass123!",
        },
        format="json",
    )
    assert confirm.status_code == 200

    relogin = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "ResetPass123!"},
        format="json",
    )
    assert relogin.status_code == 200


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(student_user):
    client = APIClient()
    login_response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "Testpass123!"},
        format="json",
    )
    access = login_response.json()["access"]
    refresh = login_response.json()["refresh"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_response = client.post(
        "/api/auth/logout/",
        {"refresh": refresh},
        format="json",
    )
    assert logout_response.status_code == 200

    refresh_response = client.post(
        "/api/auth/refresh/",
        {"refresh": refresh},
        format="json",
    )
    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_identity_availability_for_admin(admin_user, student_user):
    client = APIClient()
    login_response = client.post(
        "/api/auth/login/",
        {"identifier": admin_user.email, "password": "Testpass123!"},
        format="json",
    )
    access = login_response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/auth/identity-availability/",
        {"email": student_user.email, "matricule": "NEW-MAT-001"},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"]["available"] is False
    assert payload["matricule"]["available"] is True


@pytest.mark.django_db
def test_identity_availability_forbidden_for_student(student_user):
    client = APIClient()
    login_response = client.post(
        "/api/auth/login/",
        {"identifier": student_user.email, "password": "Testpass123!"},
        format="json",
    )
    access = login_response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/auth/identity-availability/",
        {"email": "new@example.com"},
        format="json",
    )
    assert response.status_code == 403
