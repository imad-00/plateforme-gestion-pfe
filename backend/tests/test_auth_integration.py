import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


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
