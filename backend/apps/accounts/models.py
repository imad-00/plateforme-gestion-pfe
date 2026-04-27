from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
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
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "matricule"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["business_identity"], name="accounts_user_identity_idx"),
            models.Index(fields=["account_status"], name="accounts_user_status_idx"),
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

    def refresh_platform_flags(self):
        """
        Keep Django technical flags aligned with platform grants.
        These flags are framework-level only, not business authorization source.
        """
        if not self.pk:
            return

        if self.account_status != self.AccountStatus.ACTIVE:
            target_is_staff = False
            target_is_superuser = False
        else:
            active_levels = set(
                self.platform_access_grants.filter(revoked_at__isnull=True).values_list(
                    "access_level", flat=True
                )
            )
            target_is_staff = bool(active_levels)
            target_is_superuser = self.platform_access_grants.model.AccessLevel.SUPER_ADMIN in active_levels

        if self.is_staff != target_is_staff or self.is_superuser != target_is_superuser:
            User.objects.filter(pk=self.pk).update(
                is_staff=target_is_staff,
                is_superuser=target_is_superuser,
            )
            self.is_staff = target_is_staff
            self.is_superuser = target_is_superuser


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
    annual_average = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    speciality = models.CharField(max_length=255, null=True, blank=True)
    cv_file_url = models.CharField(max_length=500, blank=True)
    skills_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_student_profile"

    def __str__(self):
        year_label = self.academic_year.year if self.academic_year else "No Academic Year"
        return f"{self.user.matricule} - {year_label}"

    # Backward compatibility aliases; source fields now follow class diagram naming.
    @property
    def moyenne_generale(self):
        return self.annual_average

    @moyenne_generale.setter
    def moyenne_generale(self, value):
        self.annual_average = value

    @property
    def specialite(self):
        return self.speciality

    @specialite.setter
    def specialite(self, value):
        self.speciality = value


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    grade = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_teacher_profile"

    def __str__(self):
        return f"{self.user.matricule} - {self.grade or 'No Grade'}"

    @property
    def departement(self):
        return self.department

    @departement.setter
    def departement(self, value):
        self.department = value


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
    expertise_area = models.CharField(max_length=255, null=True, blank=True)
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
        if self.revoked_at is None and self.user.account_status != User.AccountStatus.ACTIVE:
            raise ValidationError({"user": "Only ACTIVE users can hold active platform access grants."})

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        self.user.refresh_platform_flags()
        return result

    def delete(self, *args, **kwargs):
        user = self.user
        result = super().delete(*args, **kwargs)
        user.refresh_platform_flags()
        return result


class PasswordResetOTP(models.Model):
    """
    One-time password flow storage for password reset.
    OTP code is hashed, never stored in plaintext.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    otp_code_hash = models.CharField(max_length=128)
    verification_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_password_reset_otp"
        indexes = [
            models.Index(fields=["user"], name="acc_pwd_reset_user_idx"),
            models.Index(fields=["expires_at"], name="acc_pwd_reset_exp_idx"),
            models.Index(fields=["consumed_at"], name="acc_pwd_reset_used_idx"),
        ]

    def __str__(self):
        return f"{self.user.matricule} password-reset OTP @ {self.created_at.isoformat()}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None

    def set_otp(self, raw_otp: str):
        self.otp_code_hash = make_password(raw_otp)

    def check_otp(self, raw_otp: str) -> bool:
        return check_password(raw_otp, self.otp_code_hash)
