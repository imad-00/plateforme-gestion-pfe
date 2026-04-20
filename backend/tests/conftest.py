import pytest

from apps.accounts.models import PlatformAccessGrant, StudentProfile, TeacherProfile, User


@pytest.fixture
def user_factory(db):
    def create_user(
        *,
        matricule,
        email,
        password="Testpass123!",
        global_role=User.GlobalRole.STUDENT,
        is_active=True,
        is_archived=False,
        business_identity=None,
        account_status=None,
        is_staff=False,
        is_superuser=False,
        first_name="",
        last_name="",
        with_platform_access=False,
    ):
        if business_identity is None:
            business_identity = {
                User.GlobalRole.STUDENT: User.BusinessIdentity.STUDENT,
                User.GlobalRole.TEACHER: User.BusinessIdentity.TEACHER,
                User.GlobalRole.ADMIN: User.BusinessIdentity.ADMINISTRATIVE_STAFF,
                User.GlobalRole.SUPER_ADMIN: User.BusinessIdentity.ADMINISTRATIVE_STAFF,
            }.get(global_role, User.BusinessIdentity.STUDENT)

        if account_status is None:
            account_status = (
                User.AccountStatus.ARCHIVED
                if is_archived
                else (User.AccountStatus.ACTIVE if is_active else User.AccountStatus.SUSPENDED)
            )

        user = User.objects.create_user(
            email=email,
            matricule=matricule,
            password=password,
            global_role=global_role,
            business_identity=business_identity,
            account_status=account_status,
            is_active=is_active,
            is_archived=is_archived,
            is_staff=is_staff,
            is_superuser=is_superuser,
            first_name=first_name,
            last_name=last_name,
        )

        if global_role == User.GlobalRole.STUDENT:
            StudentProfile.objects.create(user=user)
        if global_role == User.GlobalRole.TEACHER:
            TeacherProfile.objects.create(user=user)

        if with_platform_access:
            level = (
                PlatformAccessGrant.AccessLevel.SUPER_ADMIN
                if global_role == User.GlobalRole.SUPER_ADMIN
                else PlatformAccessGrant.AccessLevel.ADMIN
            )
            PlatformAccessGrant.objects.create(user=user, access_level=level)

        return user

    return create_user


@pytest.fixture
def student_user(user_factory):
    return user_factory(
        matricule="STU001",
        email="student@example.com",
        global_role=User.GlobalRole.STUDENT,
        first_name="Student",
        last_name="One",
    )


@pytest.fixture
def teacher_user(user_factory):
    return user_factory(
        matricule="TEA001",
        email="teacher@example.com",
        global_role=User.GlobalRole.TEACHER,
        first_name="Teacher",
        last_name="One",
    )


@pytest.fixture
def admin_user(user_factory):
    return user_factory(
        matricule="ADM001",
        email="admin@example.com",
        global_role=User.GlobalRole.ADMIN,
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        first_name="Admin",
        last_name="One",
        with_platform_access=True,
    )


@pytest.fixture
def super_admin_user(user_factory):
    return user_factory(
        matricule="SADM001",
        email="superadmin@example.com",
        global_role=User.GlobalRole.SUPER_ADMIN,
        business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        is_staff=True,
        is_superuser=True,
        first_name="Super",
        last_name="Admin",
        with_platform_access=True,
    )
