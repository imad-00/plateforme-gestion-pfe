from django.db import transaction
from rest_framework import serializers

from apps.academics.models import AcademicYear


class AcademicYearSerializer(serializers.ModelSerializer):
    """
    Sprint 2 policy:
    - archived year cannot be active
    - when a year is activated, it becomes the unique active year
      by deactivating all others in the same transaction
    """

    class Meta:
        model = AcademicYear
        fields = [
            "id",
            "year",
            "is_active",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        is_archived = attrs.get(
            "is_archived", instance.is_archived if instance is not None else False
        )
        is_active = attrs.get("is_active", instance.is_active if instance is not None else False)

        if is_archived and is_active:
            raise serializers.ValidationError(
                {"is_active": "Archived academic year cannot be active."}
            )

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            # Keep a single active academic year at a time.
            if validated_data.get("is_active", False):
                AcademicYear.objects.filter(is_active=True).update(is_active=False)
            return super().create(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            # Keep a single active academic year at a time.
            if validated_data.get("is_active", False):
                AcademicYear.objects.exclude(pk=instance.pk).filter(is_active=True).update(
                    is_active=False
                )
            return super().update(instance, validated_data)
