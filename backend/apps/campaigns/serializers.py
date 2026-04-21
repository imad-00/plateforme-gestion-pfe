from rest_framework import serializers

from apps.campaigns.models import CampaignPhase


class CampaignPhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignPhase
        fields = [
            "id",
            "academic_year",
            "phase_type",
            "start_at",
            "end_at",
            "display_order",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        academic_year = attrs.get(
            "academic_year",
            instance.academic_year if instance is not None else None,
        )
        phase_type = attrs.get(
            "phase_type",
            instance.phase_type if instance is not None else None,
        )
        display_order = attrs.get(
            "display_order",
            instance.display_order if instance is not None else None,
        )
        start_at = attrs.get("start_at", instance.start_at if instance is not None else None)
        end_at = attrs.get("end_at", instance.end_at if instance is not None else None)

        if academic_year is not None and academic_year.status == "ARCHIVED":
            raise serializers.ValidationError(
                {"academic_year": "Cannot attach phase to archived academic year."}
            )

        if start_at is not None and end_at is not None and end_at < start_at:
            raise serializers.ValidationError(
                {"end_at": "end_at must be greater than or equal to start_at."}
            )

        if academic_year is not None and phase_type is not None:
            existing = CampaignPhase.objects.filter(
                academic_year=academic_year,
                phase_type=phase_type,
            )
            if instance is not None:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {"phase_type": "This phase type already exists for the selected academic year."}
                )

        if academic_year is not None and display_order is not None:
            existing = CampaignPhase.objects.filter(
                academic_year=academic_year,
                display_order=display_order,
            )
            if instance is not None:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {"display_order": "This display order is already used for the selected academic year."}
                )

        return attrs
