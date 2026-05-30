import secrets
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    ExternalSupervisorProfile,
    PasswordResetOTP,
    StudentProfile,
    TeacherProfile,
)

User = get_user_model()


class LoginRejected(APIException):
    status_code = 401
    default_detail = "Invalid identifier or password."
    default_code = "authentication_failed"


class StudentProfileSerializer(serializers.ModelSerializer):
    moyenne_generale = serializers.DecimalField(
        source="annual_average",
        max_digits=4,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    specialite = serializers.CharField(source="speciality", required=False, allow_blank=True, allow_null=True)

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


class TeacherProfileSerializer(serializers.ModelSerializer):
    departement = serializers.CharField(source="department", required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = TeacherProfile
        fields = ["grade", "department", "departement"]


class ExternalSupervisorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalSupervisorProfile
        fields = ["academic_year", "organization", "job_title", "expertise_area"]


class UserSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True)
    teacher_profile = TeacherProfileSerializer(read_only=True)
    external_supervisor_profile = ExternalSupervisorProfileSerializer(read_only=True)
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
        ]

    def get_platform_access_level(self, obj):
        active_grant = (
            obj.platform_access_grants.filter(revoked_at__isnull=True)
            .order_by("-granted_at")
            .first()
            if hasattr(obj, "platform_access_grants")
            else None
        )
        if active_grant:
            return active_grant.access_level
        return None


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid_credentials": "Invalid identifier or password.",
        "archived": "This account is archived.",
        "inactive": "This account is inactive.",
        "password_reset_required": "Password reset required. Please use forgot password.",
    }

    def _resolve_user(self, identifier):
        return (
            User.objects.filter(Q(email__iexact=identifier) | Q(matricule__iexact=identifier))
            .order_by("id")
            .first()
        )

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        password = attrs["password"]

        candidate = self._resolve_user(identifier)
        if candidate is None:
            raise LoginRejected(self.error_messages["invalid_credentials"])
        if candidate.account_status == User.AccountStatus.ARCHIVED:
            raise LoginRejected(self.error_messages["archived"])
        if candidate.account_status != User.AccountStatus.ACTIVE:
            raise LoginRejected(self.error_messages["inactive"])

        user = authenticate(
            request=self.context.get("request"),
            identifier=identifier,
            password=password,
        )

        if user is None:
            raise LoginRejected(self.error_messages["invalid_credentials"])
        if getattr(user, "must_reset_password", False):
            raise LoginRejected(self.error_messages["password_reset_required"])

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class RefreshTokenInputSerializer(TokenRefreshSerializer):
    pass


def _resolve_user_by_identifier(identifier: str):
    return (
        User.objects.filter(
            Q(email__iexact=identifier) | Q(matricule__iexact=identifier)
        )
        .order_by("id")
        .first()
    )


class PasswordResetRequestOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    default_error_messages = {
        "generic": "If this account exists and is active, an OTP has been generated.",
    }

    def create(self, validated_data):
        identifier = validated_data["identifier"].strip()
        candidate = _resolve_user_by_identifier(identifier)

        generated_otp = None
        if candidate is not None and candidate.account_status == User.AccountStatus.ACTIVE:
            PasswordResetOTP.objects.filter(
                user=candidate,
                consumed_at__isnull=True,
            ).update(consumed_at=timezone.now())

            generated_otp = f"{secrets.randbelow(10**6):06d}"
            otp_ttl_minutes = getattr(settings, "PASSWORD_RESET_OTP_TTL_MINUTES", 10)

            otp_record = PasswordResetOTP(
                user=candidate,
                expires_at=timezone.now() + timedelta(minutes=otp_ttl_minutes),
            )
            otp_record.set_otp(generated_otp)
            otp_record.save()

            send_mail(
                subject="PFE Platform - Password Reset OTP",
                message=(
                    f"Bonjour,\n\n"
                    f"Votre code OTP de réinitialisation est: {generated_otp}\n"
                    f"Ce code expire dans {otp_ttl_minutes} minutes.\n\n"
                    f"Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[candidate.email],
                fail_silently=False,
            )

        payload = {"detail": self.error_messages["generic"]}
        if settings.DEBUG and generated_otp:
            payload["otp_debug"] = generated_otp
        return payload


class PasswordResetResendOTPSerializer(PasswordResetRequestOTPSerializer):
    pass


class PasswordResetVerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp = serializers.CharField()

    default_error_messages = {
        "invalid_otp": "Invalid or expired OTP.",
    }

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        otp = attrs["otp"].strip()

        user = _resolve_user_by_identifier(identifier)
        if user is None or user.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError({"otp": self.error_messages["invalid_otp"]})

        otp_record = (
            PasswordResetOTP.objects.filter(
                user=user,
                consumed_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if otp_record is None or otp_record.is_expired or not otp_record.check_otp(otp):
            raise serializers.ValidationError({"otp": self.error_messages["invalid_otp"]})

        attrs["otp_record"] = otp_record
        return attrs

    def create(self, validated_data):
        otp_record = validated_data["otp_record"]
        if otp_record.verified_at is None:
            otp_record.verified_at = timezone.now()
        if not otp_record.verification_token:
            otp_record.verification_token = uuid4().hex
        otp_record.save(update_fields=["verified_at", "verification_token", "updated_at"])
        return {
            "detail": "OTP verified successfully.",
            "verification_token": otp_record.verification_token,
        }


class PasswordResetConfirmSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    verification_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        verification_token = attrs["verification_token"].strip()
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Password confirmation does not match."}
            )

        user = _resolve_user_by_identifier(identifier)
        if user is None or user.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError(
                {"verification_token": "Invalid reset session."}
            )

        otp_record = (
            PasswordResetOTP.objects.filter(
                user=user,
                verification_token=verification_token,
                consumed_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if otp_record is None or otp_record.verified_at is None or otp_record.is_expired:
            raise serializers.ValidationError(
                {"verification_token": "Invalid reset session."}
            )

        password_validation.validate_password(new_password, user=user)
        attrs["user"] = user
        attrs["otp_record"] = otp_record
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        otp_record = validated_data["otp_record"]
        new_password = validated_data["new_password"]

        user.set_password(new_password)
        user.must_reset_password = False
        user.save(update_fields=["password", "must_reset_password", "updated_at"])

        otp_record.consumed_at = timezone.now()
        otp_record.save(update_fields=["consumed_at", "updated_at"])

        from apps.notifications.services import NotificationService
        NotificationService.notify_password_changed(user)

        return {"detail": "Password reset completed successfully."}


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Password confirmation does not match."}
            )

        password_validation.validate_password(attrs["new_password"], user=user)
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        user.set_password(validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        from apps.notifications.services import NotificationService
        NotificationService.notify_password_changed(user)
        return {"detail": "Password changed successfully."}


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        token = attrs["refresh"].strip()
        try:
            refresh = RefreshToken(token)
            refresh.blacklist()
        except Exception:
            raise serializers.ValidationError({"refresh": "Invalid refresh token."})
        return attrs


class IdentityAvailabilitySerializer(serializers.Serializer):
    matricule = serializers.CharField(required=False, allow_blank=False)
    email = serializers.EmailField(required=False, allow_blank=False)

    def validate(self, attrs):
        if not attrs.get("matricule") and not attrs.get("email"):
            raise serializers.ValidationError(
                "Provide at least one field: matricule or email."
            )
        return attrs

    def create(self, validated_data):
        result = {}
        matricule = validated_data.get("matricule")
        if matricule:
            result["matricule"] = {
                "value": matricule,
                "available": not User.objects.filter(matricule__iexact=matricule).exists(),
            }
        email = validated_data.get("email")
        if email:
            result["email"] = {
                "value": email,
                "available": not User.objects.filter(email__iexact=email).exists(),
            }
        return result
