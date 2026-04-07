import pytest

from apps.accounts.models import StudentProfile, TeacherProfile, User


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
        is_staff=False,
        is_superuser=False,
        first_name="",
        last_name="",
    ):
        user = User.objects.create_user(
            email=email,
            matricule=matricule,
            password=password,
            global_role=global_role,
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
        is_staff=True,
        first_name="Admin",
        last_name="One",
    )


@pytest.fixture
def super_admin_user(user_factory):
    return user_factory(
        matricule="SADM001",
        email="superadmin@example.com",
        global_role=User.GlobalRole.SUPER_ADMIN,
        is_staff=True,
        is_superuser=True,
        first_name="Super",
        last_name="Admin",
    )
