from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import PlatformAccessGrant

User = get_user_model()


class PlatformAccessGrantUserSerializer(serializers.ModelSerializer):
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
        ]


class PlatformAccessGrantReadSerializer(serializers.ModelSerializer):
    user = PlatformAccessGrantUserSerializer(read_only=True)
    granted_by = PlatformAccessGrantUserSerializer(read_only=True)

    class Meta:
        model = PlatformAccessGrant
        fields = [
            "id",
            "user",
            "access_level",
            "granted_by",
            "granted_at",
            "revoked_at",
            "created_at",
            "updated_at",
        ]


class PlatformAccessGrantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAccessGrant
        fields = ["user", "access_level"]

    def validate_user(self, value):
        if value.business_identity in {
            User.BusinessIdentity.STUDENT,
            User.BusinessIdentity.EXTERNAL_SUPERVISOR,
        }:
            raise serializers.ValidationError(
                "Platform access can be granted only to TEACHER or ADMINISTRATIVE_STAFF users."
            )
        if value.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError("Only ACTIVE users can receive platform access.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        actor = self.context.get("actor")
        user = validated_data["user"]
        access_level = validated_data["access_level"]

        # lock existing grants for this user to keep one-active-grant invariant stable
        PlatformAccessGrant.objects.select_for_update().filter(user=user)

        try:
            grant = PlatformAccessGrant.objects.create(
                user=user,
                access_level=access_level,
                granted_by=actor,
                granted_at=timezone.now(),
            )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"user": "This user already has an active platform access grant."}
            ) from exc

        user.is_staff = True
        if access_level == PlatformAccessGrant.AccessLevel.SUPER_ADMIN:
            user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser", "updated_at"])

        return grant


class PlatformAccessGrantRevokeSerializer(serializers.Serializer):
    revoked_at = serializers.DateTimeField(required=False)

    @transaction.atomic
    def revoke(self, grant: PlatformAccessGrant):
        if grant.revoked_at is not None:
            raise serializers.ValidationError({"detail": "Platform access grant is already revoked."})

        revoked_at = self.validated_data.get("revoked_at", timezone.now())
        grant.revoked_at = revoked_at
        grant.save(update_fields=["revoked_at", "updated_at"])

        user = grant.user
        has_other_active_grants = user.platform_access_grants.filter(revoked_at__isnull=True).exists()
        if not has_other_active_grants:
            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=["is_staff", "is_superuser", "updated_at"])

        return grant
