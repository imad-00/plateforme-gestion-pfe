from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class GlobalRole(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"
        ADMIN = "ADMIN", "Admin"
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"

    class BusinessIdentity(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"
        ADMINISTRATIVE_STAFF = "ADMINISTRATIVE_STAFF", "Administrative Staff"
        EXTERNAL_SUPERVISOR = "EXTERNAL_SUPERVISOR", "External Supervisor"

    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        ARCHIVED = "ARCHIVED", "Archived"

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
    # Deprecated business field kept temporarily for backward compatibility.
    # Access decisions now rely on business_identity + platform access grants.
    business_identity = models.CharField(
        max_length=30,
        choices=BusinessIdentity.choices,
        default=BusinessIdentity.STUDENT,
    )
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
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
            models.Index(fields=["business_identity"], name="accounts_user_identity_idx"),
            models.Index(fields=["account_status"], name="accounts_user_status_idx"),
            models.Index(fields=["is_archived"], name="accounts_user_archived_idx"),
        ]

    def __str__(self):
        return f"{self.email} ({self.matricule})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_account_accessible(self):
        """Source of truth for user accessibility."""
        return self.account_status == self.AccountStatus.ACTIVE

    def save(self, *args, **kwargs):
        # Keep legacy boolean flags coherent with the new enum status.
        if self.account_status == self.AccountStatus.ACTIVE:
            self.is_active = True
            self.is_archived = False
        elif self.account_status == self.AccountStatus.SUSPENDED:
            self.is_active = False
            self.is_archived = False
        elif self.account_status == self.AccountStatus.ARCHIVED:
            self.is_active = False
            self.is_archived = True
        return super().save(*args, **kwargs)


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


class AdministrativeStaffProfile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="administrative_staff_profile",
    )
    position = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_administrative_staff_profile"

    def __str__(self):
        return f"{self.user.matricule} - {self.position or 'No Position'}"


class ExternalSupervisorProfile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="external_supervisor_profile",
    )
    organization = models.CharField(max_length=255, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_external_supervisor_profile"

    def __str__(self):
        return f"{self.user.matricule} - {self.organization or 'No Organization'}"


class PlatformAccessGrant(models.Model):
    class AccessLevel(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="platform_access_grants",
    )
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices)
    granted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="granted_platform_accesses",
        null=True,
        blank=True,
    )
    granted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_platform_access_grant"
        indexes = [
            models.Index(fields=["user"], name="acc_plat_access_user_idx"),
            models.Index(fields=["access_level"], name="acc_plat_access_lvl_idx"),
            models.Index(fields=["revoked_at"], name="acc_plat_access_rev_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(revoked_at__isnull=True),
                name="accounts_one_active_platform_access_per_user",
            )
        ]

    def __str__(self):
        status = "active" if self.revoked_at is None else f"revoked@{self.revoked_at.isoformat()}"
        return f"{self.user.matricule} - {self.access_level} ({status})"

    @property
    def is_active(self):
        return self.revoked_at is None

    def clean(self):
        if self.user.business_identity in {
            User.BusinessIdentity.STUDENT,
            User.BusinessIdentity.EXTERNAL_SUPERVISOR,
        }:
            raise ValidationError(
                {"user": "Platform access can be granted only to TEACHER or ADMINISTRATIVE_STAFF users."}
            )

        if self.revoked_at is not None and self.revoked_at < self.granted_at:
            raise ValidationError({"revoked_at": "revoked_at cannot be before granted_at."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
