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
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"status": {"validators": []}}

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        status = attrs.get("status", instance.status if instance is not None else AcademicYear.Status.CLOSED)
        if status not in AcademicYear.Status.values:
            raise serializers.ValidationError({"status": "Invalid academic year status."})
        return attrs

    def _archive_other_years(self, *, exclude_pk=None):
        queryset = AcademicYear.objects.select_for_update()
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        queryset.update(status=AcademicYear.Status.ARCHIVED)

    def create(self, validated_data):
        with transaction.atomic():
            if validated_data.get("status") == AcademicYear.Status.ACTIVE:
                self._archive_other_years()
            try:
                return super().create(validated_data)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"status": "Only one academic year can be ACTIVE at a time."}
                ) from exc

    def update(self, instance, validated_data):
        with transaction.atomic():
            if validated_data.get("status") == AcademicYear.Status.ACTIVE:
                self._archive_other_years(exclude_pk=instance.pk)
            try:
                return super().update(instance, validated_data)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"status": "Only one academic year can be ACTIVE at a time."}
                ) from exc
