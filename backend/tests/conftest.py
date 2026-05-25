from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import PlatformAccessGrant, StudentProfile, TeacherProfile, User
from apps.campaigns.models import CampaignPhase


@pytest.fixture
def user_factory(db):
    def create_user(
        *,
        matricule,
        email,
        password="Testpass123!",
        business_identity=User.BusinessIdentity.STUDENT,
        account_status=User.AccountStatus.ACTIVE,
        is_staff=False,
        is_superuser=False,
        first_name="",
        last_name="",
        with_platform_access=False,
        platform_access_level=PlatformAccessGrant.AccessLevel.ADMIN,
    ):
        user = User.objects.create_user(
            email=email,
            matricule=matricule,
            password=password,
            business_identity=business_identity,
            account_status=account_status,
            is_staff=is_staff,
            is_superuser=is_superuser,
            first_name=first_name,
            last_name=last_name,
        )

        if business_identity == User.BusinessIdentity.STUDENT:
            StudentProfile.objects.create(user=user)
        if business_identity == User.BusinessIdentity.TEACHER:
            TeacherProfile.objects.create(user=user)

        if with_platform_access:
            PlatformAccessGrant.objects.create(
                user=user,
                access_level=platform_access_level,
            )
            user.is_staff = True
            user.is_superuser = platform_access_level == PlatformAccessGrant.AccessLevel.SUPER_ADMIN
            user.save(update_fields=["is_staff", "is_superuser", "updated_at"])

        return user

    return create_user


@pytest.fixture
def student_user(user_factory):
    return user_factory(
        matricule="STU001",
        email="student@example.com",
        business_identity=User.BusinessIdentity.STUDENT,
        first_name="Student",
        last_name="One",
    )


@pytest.fixture
def teacher_user(user_factory):
    return user_factory(
        matricule="TEA001",
        email="teacher@example.com",
        business_identity=User.BusinessIdentity.TEACHER,
        first_name="Teacher",
        last_name="One",
    )


@pytest.fixture
def admin_user(user_factory):
    return user_factory(
        matricule="ADM001",
        email="admin@example.com",
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        first_name="Admin",
        last_name="One",
        with_platform_access=True,
        platform_access_level=PlatformAccessGrant.AccessLevel.ADMIN,
    )


@pytest.fixture
def super_admin_user(user_factory):
    return user_factory(
        matricule="SADM001",
        email="superadmin@example.com",
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        is_superuser=True,
        first_name="Super",
        last_name="Admin",
        with_platform_access=True,
        platform_access_level=PlatformAccessGrant.AccessLevel.SUPER_ADMIN,
    )


@pytest.fixture
def open_campaign_phase(db):
    def create_phase(academic_year, phase_type, *, display_order=1, days_before=1, days_after=1):
        now = timezone.now()
        return CampaignPhase.objects.create(
            academic_year=academic_year,
            phase_type=phase_type,
            start_at=now - timedelta(days=days_before),
            end_at=now + timedelta(days=days_after) if days_after is not None else None,
            display_order=display_order,
        )

    return create_phase
