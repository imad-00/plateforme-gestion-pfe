from datetime import datetime, timezone as dt_timezone

from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.academics.models import AcademicYear


# Sentinel start_at for auto-created phases. The phase exists so the admin can
# schedule it, but is_open() returns False until the admin moves start_at into
# the past. Choosing a far-future fixed timestamp keeps the row valid against
# the NOT NULL constraint without surprising anyone with "phase opens in 1970".
_PHASE_SENTINEL_START = datetime(2099, 12, 31, tzinfo=dt_timezone.utc)


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

    @transaction.atomic
    def create(self, validated_data):
        try:
            year = super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"status": "Only one academic year can be ACTIVE at a time."}
            ) from exc

        # Phase types are an enum, not user-created. As soon as a year is ACTIVE,
        # auto-create one record per PhaseType with a sentinel start (not yet
        # open). The admin then reschedules + opens phases via PATCH.
        if year.status == AcademicYear.Status.ACTIVE:
            self._auto_create_phases(year)
            actor = getattr(self.context.get("request", None), "user", None)
            from apps.notifications.services import NotificationService
            NotificationService.notify_academic_year_opened(year, actor=actor)
        return year

    @staticmethod
    def _auto_create_phases(year):
        # Imported lazily to avoid a circular import at module load.
        from apps.campaigns.models import CampaignPhase

        existing = set(
            CampaignPhase.objects.filter(academic_year=year).values_list("phase_type", flat=True)
        )
        for order, phase_type in enumerate(CampaignPhase.PhaseType.values, start=1):
            if phase_type in existing:
                continue
            CampaignPhase.objects.create(
                academic_year=year,
                phase_type=phase_type,
                start_at=_PHASE_SENTINEL_START,
                end_at=None,
                display_order=order,
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"status": "Only one academic year can be ACTIVE at a time."}
            ) from exc
