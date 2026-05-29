from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.defenses.models import Defense, DefenseAttachedFile, DefenseJuryAssignment, DefenseSupervisorDecision
from apps.deliverables.serializers import DeliverableFileSerializer
from apps.teams.serializers import TeamSerializer, TeamUserSummarySerializer

User = get_user_model()


class DefenseAttachedFileSerializer(serializers.ModelSerializer):
    deliverable_file = DeliverableFileSerializer(read_only=True)
    added_by = TeamUserSummarySerializer(read_only=True)

    class Meta:
        model = DefenseAttachedFile
        fields = ["id", "deliverable_file", "order", "added_by", "added_at"]


class DefenseSupervisorDecisionSerializer(serializers.ModelSerializer):
    supervisor = TeamUserSummarySerializer(read_only=True)

    class Meta:
        model = DefenseSupervisorDecision
        fields = ["id", "supervisor", "decision", "decided_at"]


class DefenseJuryAssignmentSerializer(serializers.ModelSerializer):
    user = TeamUserSummarySerializer(read_only=True)
    assigned_by = TeamUserSummarySerializer(read_only=True)

    class Meta:
        model = DefenseJuryAssignment
        fields = ["id", "user", "role", "assigned_by", "assigned_at"]


class DefenseSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Defense
        fields = [
            "id",
            "team",
            "status",
            "requested_by",
            "requested_at",
            "scheduled_at",
            "location",
            "scheduled_by",
            "final_grade",
            "deliberation",
            "pv_file",
            "pv_uploaded_by",
            "pv_uploaded_at",
            "created_at",
            "updated_at",
        ]


class DefenseDetailSerializer(DefenseSerializer):
    requested_by = TeamUserSummarySerializer(read_only=True)
    scheduled_by = TeamUserSummarySerializer(read_only=True)
    pv_uploaded_by = TeamUserSummarySerializer(read_only=True)
    attached_files = DefenseAttachedFileSerializer(many=True, read_only=True)
    supervisor_decisions = DefenseSupervisorDecisionSerializer(many=True, read_only=True)
    jury_assignments = DefenseJuryAssignmentSerializer(many=True, read_only=True)
    pv_file_url = serializers.SerializerMethodField()

    class Meta(DefenseSerializer.Meta):
        fields = DefenseSerializer.Meta.fields + [
            "pv_file_url",
            "attached_files",
            "supervisor_decisions",
            "jury_assignments",
        ]

    def get_pv_file_url(self, obj):
        if not obj.pv_file:
            return ""
        try:
            return obj.pv_file.url
        except Exception:
            return ""


class DefenseRequestSerializer(serializers.Serializer):
    existing_file_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    ordering = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )


class SupervisorDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            DefenseSupervisorDecision.DecisionStatus.ACCEPTED,
            DefenseSupervisorDecision.DecisionStatus.DENIED,
        ]
    )


class ScheduleDefenseSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    location = serializers.CharField(required=False, allow_blank=True)
    president_user_id = serializers.IntegerField()
    examiner_user_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    guest_user_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)

    def get_president_user(self):
        return User.objects.filter(id=self.validated_data["president_user_id"]).first()

    def get_examiner_users(self):
        return list(User.objects.filter(id__in=self.validated_data["examiner_user_ids"]))

    def get_guest_users(self):
        guest_ids = self.validated_data.get("guest_user_ids", [])
        return list(User.objects.filter(id__in=guest_ids))


class RescheduleDefenseSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one field to update.")
        return attrs


class UpdateJurySerializer(ScheduleDefenseSerializer):
    pass


class UpdateDefenseFilesSerializer(serializers.Serializer):
    existing_file_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    remove_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    ordering = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )


class UploadPVSerializer(serializers.Serializer):
    final_grade = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=20)
    deliberation = serializers.CharField()
    pv_file = serializers.FileField()

    def validate_deliberation(self, value):
        if not value.strip():
            raise serializers.ValidationError("Deliberation is required.")
        return value.strip()
