from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class GlobalRole(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"
        ADMIN = "ADMIN", "Admin"
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"

    id = models.BigAutoField(primary_key=True)
    matricule = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    global_role = models.CharField(
        max_length=20,
        choices=GlobalRole.choices,
        default=GlobalRole.STUDENT,
    )
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "matricule"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["global_role"], name="accounts_user_role_idx"),
            models.Index(fields=["is_archived"], name="accounts_user_archived_idx"),
        ]

    def __str__(self):
        return f"{self.email} ({self.matricule})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class StudentProfile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.SET_NULL,
        related_name="student_profiles",
        null=True,
        blank=True,
    )
    moyenne_generale = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    specialite = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_student_profile"

    def __str__(self):
        year_label = self.academic_year.year if self.academic_year else "No Academic Year"
        return f"{self.user.matricule} - {year_label}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    grade = models.CharField(max_length=255, null=True, blank=True)
    departement = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_teacher_profile"

    def __str__(self):
        return f"{self.user.matricule} - {self.grade or 'No Grade'}"
