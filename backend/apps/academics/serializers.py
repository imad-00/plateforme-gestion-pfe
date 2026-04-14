from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.academics.models import AcademicYear


class AcademicYearSerializer(serializers.ModelSerializer):
    """
    Academic year governance policy:
    - archived year cannot be active
    - only one year can be active at a time
    - activating one year archives/deactivates all others
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
        extra_kwargs = {"is_active": {"validators": []}}

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

    def _archive_and_deactivate_other_years(self, *, exclude_pk=None):
        queryset = AcademicYear.objects.select_for_update()
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        queryset.update(is_active=False, is_archived=True)

    def create(self, validated_data):
        with transaction.atomic():
            if validated_data.get("is_active", False):
                self._archive_and_deactivate_other_years()
                validated_data["is_archived"] = False
            try:
                return super().create(validated_data)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"is_active": "Only one academic year can be active at a time."}
                ) from exc

    def update(self, instance, validated_data):
        with transaction.atomic():
            if validated_data.get("is_active", False):
                self._archive_and_deactivate_other_years(exclude_pk=instance.pk)
                validated_data["is_archived"] = False
            try:
                return super().update(instance, validated_data)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"is_active": "Only one academic year can be active at a time."}
                ) from exc
