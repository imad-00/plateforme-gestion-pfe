from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import StudentProfile, TeacherProfile
from apps.academics.models import AcademicYear

User = get_user_model()


class StudentProfileAdminSerializer(serializers.ModelSerializer):
    def validate_academic_year(self, value):
        if value is None:
            return value
        if value.is_archived or not value.is_active:
            raise serializers.ValidationError(
                "Student profile must be linked to the active academic year."
            )
        return value

    class Meta:
        model = StudentProfile
        fields = ["academic_year", "moyenne_generale", "specialite"]


class TeacherProfileAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = ["grade", "departement"]


class AdminUserListSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileAdminSerializer(read_only=True)
    teacher_profile = TeacherProfileAdminSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "matricule",
            "email",
            "first_name",
            "last_name",
            "global_role",
            "is_active",
            "is_archived",
            "student_profile",
            "teacher_profile",
            "created_at",
            "updated_at",
        ]


class AdminUserCreateUpdateSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileAdminSerializer(required=False, allow_null=True)
    teacher_profile = TeacherProfileAdminSerializer(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "matricule",
            "email",
            "first_name",
            "last_name",
            "global_role",
            "is_active",
            "student_profile",
            "teacher_profile",
            "password",
        ]

    def _validate_actor_role_scope(self, role):
        actor = self.context.get("actor")
        if actor is None:
            return

        # Sprint 2 guardrail: ADMIN cannot escalate or manage admin-tier roles.
        if actor.global_role == User.GlobalRole.ADMIN and role not in {
            User.GlobalRole.STUDENT,
            User.GlobalRole.TEACHER,
        }:
            raise serializers.ValidationError(
                {"global_role": "ADMIN can only create/update STUDENT or TEACHER accounts."}
            )

    def _get_active_academic_year(self):
        return AcademicYear.objects.filter(is_active=True, is_archived=False).first()

    def validate(self, attrs):
        role = attrs.get("global_role", getattr(self.instance, "global_role", None))
        student_data = attrs.get("student_profile")
        teacher_data = attrs.get("teacher_profile")
        self._validate_actor_role_scope(role)

        if role == User.GlobalRole.STUDENT and teacher_data is not None:
            raise serializers.ValidationError(
                {"teacher_profile": "Teacher profile is not allowed for STUDENT role."}
            )

        if role == User.GlobalRole.TEACHER and student_data is not None:
            raise serializers.ValidationError(
                {"student_profile": "Student profile is not allowed for TEACHER role."}
            )

        if role in {User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN}:
            if student_data is not None or teacher_data is not None:
                raise serializers.ValidationError(
                    "Admin roles must not include student or teacher profile payload."
                )

        if role == User.GlobalRole.STUDENT:
            active_year = self._get_active_academic_year()
            if active_year is None:
                raise serializers.ValidationError(
                    {"student_profile": "No active academic year is configured."}
                )

        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        student_data = validated_data.pop("student_profile", None)
        teacher_data = validated_data.pop("teacher_profile", None)
        password = validated_data.pop("password")

        role = validated_data.get("global_role")
        if role in {User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN}:
            validated_data["is_staff"] = True
            validated_data["is_superuser"] = role == User.GlobalRole.SUPER_ADMIN
        else:
            validated_data["is_staff"] = False
            validated_data["is_superuser"] = False

        user = User.objects.create_user(password=password, **validated_data)
        self._sync_profiles(user, student_data, teacher_data)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        student_data = validated_data.pop("student_profile", None)
        teacher_data = validated_data.pop("teacher_profile", None)
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if instance.global_role in {User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN}:
            instance.is_staff = True
            instance.is_superuser = instance.global_role == User.GlobalRole.SUPER_ADMIN
        else:
            instance.is_staff = False
            instance.is_superuser = False

        if password:
            instance.set_password(password)

        instance.save()
        self._sync_profiles(instance, student_data, teacher_data)
        return instance

    def _sync_profiles(self, user, student_data, teacher_data):
        role = user.global_role

        if role == User.GlobalRole.STUDENT:
            active_year = self._get_active_academic_year()
            if active_year is None:
                raise serializers.ValidationError(
                    {"student_profile": "No active academic year is configured."}
                )

            effective_student_data = dict(student_data or {})
            provided_year = effective_student_data.get("academic_year")
            if provided_year is not None and provided_year.id != active_year.id:
                raise serializers.ValidationError(
                    {"student_profile": {"academic_year": "Student profile must use the active academic year."}}
                )
            effective_student_data["academic_year"] = active_year
            StudentProfile.objects.update_or_create(user=user, defaults=effective_student_data)
            TeacherProfile.objects.filter(user=user).delete()
            return

        if role == User.GlobalRole.TEACHER:
            if teacher_data is not None:
                TeacherProfile.objects.update_or_create(user=user, defaults=teacher_data)
            else:
                TeacherProfile.objects.get_or_create(user=user)
            StudentProfile.objects.filter(user=user).delete()
            return

        StudentProfile.objects.filter(user=user).delete()
        TeacherProfile.objects.filter(user=user).delete()


class SuperAdminCreateAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    global_role = serializers.ChoiceField(
        choices=[User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN],
        required=False,
        default=User.GlobalRole.ADMIN,
    )

    class Meta:
        model = User
        fields = ["matricule", "email", "first_name", "last_name", "password", "global_role"]

    def validate_global_role(self, value):
        if value not in {User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN}:
            raise serializers.ValidationError("Only ADMIN or SUPER_ADMIN can be created here.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.get("global_role", User.GlobalRole.ADMIN)
        return User.objects.create_user(
            password=password,
            is_staff=True,
            is_superuser=(role == User.GlobalRole.SUPER_ADMIN),
            **validated_data,
        )
