from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import (
    ExternalSupervisorProfile,
    PlatformAccessGrant,
    StudentProfile,
    TeacherProfile,
)
from apps.accounts.permissions import get_platform_levels
from apps.academics.models import AcademicYear

User = get_user_model()


class StudentProfileAdminSerializer(serializers.ModelSerializer):
    moyenne_generale = serializers.DecimalField(
        source="annual_average",
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    specialite = serializers.CharField(source="speciality", required=False, allow_blank=True, allow_null=True)

    def validate_academic_year(self, value):
        if value is None:
            return value
        if value.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError(
                "Student profile must be linked to the active academic year."
            )
        return value

    class Meta:
        model = StudentProfile
        fields = [
            "academic_year",
            "annual_average",
            "moyenne_generale",
            "speciality",
            "specialite",
            "cv_file_url",
            "skills_summary",
        ]


class TeacherProfileAdminSerializer(serializers.ModelSerializer):
    departement = serializers.CharField(source="department", required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = TeacherProfile
        fields = ["grade", "department", "departement"]


class ExternalSupervisorProfileAdminSerializer(serializers.ModelSerializer):
    # Mirrors StudentProfileAdminSerializer: must point at the active year.
    # The AdminUserCreateUpdateSerializer._sync_profiles auto-fills it when
    # the caller omits the field.

    def validate_academic_year(self, value):
        if value is None:
            return value
        if value.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError(
                "External supervisor profile must be linked to the active academic year."
            )
        return value

    class Meta:
        model = ExternalSupervisorProfile
        fields = ["academic_year", "organization", "job_title", "expertise_area"]


class AdminUserListSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileAdminSerializer(read_only=True)
    teacher_profile = TeacherProfileAdminSerializer(read_only=True)
    external_supervisor_profile = ExternalSupervisorProfileAdminSerializer(read_only=True)
    platform_access_level = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "matricule",
            "email",
            "first_name",
            "last_name",
            "business_identity",
            "account_status",
            "must_reset_password",
            "platform_access_level",
            "student_profile",
            "teacher_profile",
            "external_supervisor_profile",
            "created_at",
            "updated_at",
        ]

    def get_platform_access_level(self, obj):
        active_grant = (
            obj.platform_access_grants.filter(revoked_at__isnull=True)
            .order_by("-granted_at")
            .first()
            if hasattr(obj, "platform_access_grants")
            else None
        )
        return active_grant.access_level if active_grant else None


class AdminUserCreateUpdateSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileAdminSerializer(required=False, allow_null=True)
    teacher_profile = TeacherProfileAdminSerializer(required=False, allow_null=True)
    external_supervisor_profile = ExternalSupervisorProfileAdminSerializer(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "matricule",
            "email",
            "first_name",
            "last_name",
            "business_identity",
            "account_status",
            "must_reset_password",
            "student_profile",
            "teacher_profile",
            "external_supervisor_profile",
            "password",
        ]

    def _validate_actor_scope(self, identity):
        actor = self.context.get("actor")
        if actor is None:
            return

        actor_levels = get_platform_levels(actor)
        if (
            "ADMIN" in actor_levels
            and "SUPER_ADMIN" not in actor_levels
            and identity not in {
                User.BusinessIdentity.STUDENT,
                User.BusinessIdentity.TEACHER,
            }
        ):
            raise serializers.ValidationError(
                {
                    "business_identity": (
                        "ADMIN can only create/update STUDENT or TEACHER accounts."
                    )
                }
            )

    def _get_active_academic_year(self):
        return AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()

    def validate(self, attrs):
        identity = attrs.get(
            "business_identity",
            getattr(self.instance, "business_identity", User.BusinessIdentity.STUDENT),
        )
        student_data = attrs.get("student_profile")
        teacher_data = attrs.get("teacher_profile")
        external_data = attrs.get("external_supervisor_profile")
        self._validate_actor_scope(identity)

        if identity == User.BusinessIdentity.STUDENT and (teacher_data is not None or external_data is not None):
            raise serializers.ValidationError(
                "STUDENT identity must not include teacher or external supervisor profile payload."
            )

        if identity == User.BusinessIdentity.TEACHER and (student_data is not None or external_data is not None):
            raise serializers.ValidationError(
                "TEACHER identity must not include student or external supervisor profile payload."
            )

        if identity == User.BusinessIdentity.EXTERNAL_SUPERVISOR and (student_data is not None or teacher_data is not None):
            raise serializers.ValidationError(
                "EXTERNAL_SUPERVISOR identity must not include student or teacher profile payload."
            )

        if identity == User.BusinessIdentity.ADMINISTRATIVE_STAFF and any(
            payload is not None for payload in (student_data, teacher_data, external_data)
        ):
            raise serializers.ValidationError(
                "Administrative staff identity must not include any role-specific profile payload."
            )

        # Year-scoped identities (students + externals) require an active year
        # at creation. The _sync_profiles step writes it onto the profile.
        if identity in {User.BusinessIdentity.STUDENT, User.BusinessIdentity.EXTERNAL_SUPERVISOR}:
            active_year = self._get_active_academic_year()
            if active_year is None:
                key = (
                    "student_profile"
                    if identity == User.BusinessIdentity.STUDENT
                    else "external_supervisor_profile"
                )
                raise serializers.ValidationError(
                    {key: "No active academic year is configured."}
                )

        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})

        attrs.setdefault("account_status", User.AccountStatus.ACTIVE)

        target_status = attrs.get(
            "account_status",
            getattr(self.instance, "account_status", User.AccountStatus.ACTIVE),
        )
        if (
            self.instance is not None
            and target_status != User.AccountStatus.ACTIVE
            and self.instance.platform_access_grants.filter(revoked_at__isnull=True).exists()
        ):
            raise serializers.ValidationError(
                {
                    "account_status": (
                        "Revoke active platform access grants before suspending or archiving this account."
                    )
                }
            )
        return attrs

    def _sync_platform_flags(self, user):
        if user.account_status != User.AccountStatus.ACTIVE:
            user.is_staff = False
            user.is_superuser = False
            return

        active_levels = set(
            user.platform_access_grants.filter(revoked_at__isnull=True).values_list(
                "access_level", flat=True
            )
        )
        user.is_staff = bool(active_levels)
        user.is_superuser = PlatformAccessGrant.AccessLevel.SUPER_ADMIN in active_levels

    @transaction.atomic
    def create(self, validated_data):
        student_data = validated_data.pop("student_profile", None)
        teacher_data = validated_data.pop("teacher_profile", None)
        external_data = validated_data.pop("external_supervisor_profile", None)
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        self._sync_platform_flags(user)
        user.save(update_fields=["is_staff", "is_superuser", "updated_at"])
        self._sync_profiles(user, student_data, teacher_data, external_data)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        student_data = validated_data.pop("student_profile", None)
        teacher_data = validated_data.pop("teacher_profile", None)
        external_data = validated_data.pop("external_supervisor_profile", None)
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        self._sync_platform_flags(instance)
        instance.save()
        self._sync_profiles(instance, student_data, teacher_data, external_data)
        return instance

    def _sync_profiles(self, user, student_data, teacher_data, external_data):
        identity = user.business_identity

        if identity == User.BusinessIdentity.STUDENT:
            active_year = self._get_active_academic_year()
            if active_year is None:
                raise serializers.ValidationError(
                    {"student_profile": "No active academic year is configured."}
                )

            effective_student_data = dict(student_data or {})
            provided_year = effective_student_data.get("academic_year")
            if provided_year is not None and provided_year.id != active_year.id:
                raise serializers.ValidationError(
                    {
                        "student_profile": {
                            "academic_year": "Student profile must use the active academic year."
                        }
                    }
                )
            effective_student_data["academic_year"] = active_year
            StudentProfile.objects.update_or_create(user=user, defaults=effective_student_data)
            from apps.teams.services import TeamService

            TeamService.create_solo_team_for_student(user, academic_year=active_year)
            TeacherProfile.objects.filter(user=user).delete()
            ExternalSupervisorProfile.objects.filter(user=user).delete()
            return

        if identity == User.BusinessIdentity.TEACHER:
            if teacher_data is not None:
                TeacherProfile.objects.update_or_create(user=user, defaults=teacher_data)
            else:
                TeacherProfile.objects.get_or_create(user=user)
            StudentProfile.objects.filter(user=user).delete()
            ExternalSupervisorProfile.objects.filter(user=user).delete()
            return

        if identity == User.BusinessIdentity.EXTERNAL_SUPERVISOR:
            active_year = self._get_active_academic_year()
            if active_year is None:
                raise serializers.ValidationError(
                    {"external_supervisor_profile": "No active academic year is configured."}
                )

            effective_external_data = dict(external_data or {})
            provided_year = effective_external_data.get("academic_year")
            if provided_year is not None and provided_year.id != active_year.id:
                raise serializers.ValidationError(
                    {
                        "external_supervisor_profile": {
                            "academic_year": "External supervisor must use the active academic year."
                        }
                    }
                )
            effective_external_data["academic_year"] = active_year
            ExternalSupervisorProfile.objects.update_or_create(user=user, defaults=effective_external_data)
            StudentProfile.objects.filter(user=user).delete()
            TeacherProfile.objects.filter(user=user).delete()
            return

        StudentProfile.objects.filter(user=user).delete()
        TeacherProfile.objects.filter(user=user).delete()
        ExternalSupervisorProfile.objects.filter(user=user).delete()


class SuperAdminCreateAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    access_level = serializers.ChoiceField(
        choices=PlatformAccessGrant.AccessLevel.choices,
        required=False,
        default=PlatformAccessGrant.AccessLevel.ADMIN,
    )

    class Meta:
        model = User
        fields = ["matricule", "email", "first_name", "last_name", "password", "access_level"]

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        access_level = validated_data.pop("access_level")
        actor = self.context.get("actor")

        user = User.objects.create_user(
            password=password,
            business_identity=User.BusinessIdentity.ADMINISTRATIVE_STAFF,
            account_status=User.AccountStatus.ACTIVE,
            **validated_data,
        )
        PlatformAccessGrant.objects.create(
            user=user,
            access_level=access_level,
            granted_by=actor,
        )
        user.is_staff = True
        user.is_superuser = access_level == PlatformAccessGrant.AccessLevel.SUPER_ADMIN
        user.save(update_fields=["is_staff", "is_superuser", "updated_at"])
        return user
