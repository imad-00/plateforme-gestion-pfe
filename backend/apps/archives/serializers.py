from rest_framework import serializers

from apps.archives.models import AcademicYearLifecycleEvent


class AcademicYearLifecycleActionSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True)
    confirm = serializers.BooleanField()
    force = serializers.BooleanField(required=False, default=False)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("A human reason is required.")
        return value.strip()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError("This lifecycle action requires confirm=true.")
        return value


class AcademicYearLifecycleEventSerializer(serializers.ModelSerializer):
    performed_by = serializers.SerializerMethodField()

    class Meta:
        model = AcademicYearLifecycleEvent
        fields = [
            "id",
            "academic_year",
            "event_type",
            "performed_by",
            "performed_at",
            "reason",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_performed_by(self, obj):
        return {
            "id": obj.performed_by_id,
            "matricule": obj.performed_by.matricule,
            "email": obj.performed_by.email,
            "full_name": obj.performed_by.full_name,
        }
