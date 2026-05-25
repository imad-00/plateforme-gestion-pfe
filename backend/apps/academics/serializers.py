from django.db import IntegrityError
from rest_framework import serializers

from apps.academics.models import AcademicYear


class AcademicYearSerializer(serializers.ModelSerializer):
    # Read/write alias aligned with class diagram naming.
    year_label = serializers.CharField(source="year", required=False)

    class Meta:
        model = AcademicYear
        fields = [
            "id",
            "year",
            "year_label",
            "start_date",
            "end_date",
            "status",
            "wishlist_size",
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
        if instance is not None and "status" in attrs and attrs["status"] != instance.status:
            raise serializers.ValidationError(
                {"status": "Use the super-admin lifecycle endpoints to close, reopen, or archive academic years."}
            )
        wishlist_size = attrs.get(
            "wishlist_size",
            getattr(instance, "wishlist_size", 5),
        )
        if wishlist_size < 1:
            raise serializers.ValidationError({"wishlist_size": "Wishlist size must be at least 1."})
        if instance is None:
            latest_year = AcademicYear.objects.order_by("-created_at").first()
            if latest_year is not None and latest_year.status == AcademicYear.Status.ACTIVE:
                raise serializers.ValidationError(
                    {"academic_year": "Close or archive the active academic year before creating a new one."}
                )
            if status == AcademicYear.Status.ACTIVE and AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).exists():
                raise serializers.ValidationError({"status": "Only one academic year can be ACTIVE at a time."})
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"status": "Only one academic year can be ACTIVE at a time."}
            ) from exc

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"status": "Only one academic year can be ACTIVE at a time."}
            ) from exc
