from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import StudentProfile, TeacherProfile

User = get_user_model()


class LoginRejected(APIException):
    status_code = 401
    default_detail = "Invalid identifier or password."
    default_code = "authentication_failed"


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ["academic_year", "moyenne_generale", "specialite"]


class TeacherProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = ["grade", "departement"]


class UserSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True)
    teacher_profile = TeacherProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "matricule",
            "email",
            "first_name",
            "last_name",
            "global_role",
            "is_archived",
            "student_profile",
            "teacher_profile",
        ]


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid_credentials": "Invalid identifier or password.",
        "archived": "This account is archived.",
        "inactive": "This account is inactive.",
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
        if candidate.is_archived:
            raise LoginRejected(self.error_messages["archived"])
        if not candidate.is_active:
            raise LoginRejected(self.error_messages["inactive"])

        user = authenticate(
            request=self.context.get("request"),
            identifier=identifier,
            password=password,
        )

        if user is None:
            raise LoginRejected(self.error_messages["invalid_credentials"])

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class RefreshTokenInputSerializer(TokenRefreshSerializer):
    pass
