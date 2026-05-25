from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.teams.models import Team, TeamParticipant

User = get_user_model()


class TeamUserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "matricule", "email", "first_name", "last_name", "business_identity"]


class TeamParticipantSerializer(serializers.ModelSerializer):
    user = TeamUserSummarySerializer(read_only=True)

    class Meta:
        model = TeamParticipant
        fields = [
            "participation_id",
            "user",
            "role",
            "status",
            "joined_at",
            "ended_at",
            "created_at",
            "updated_at",
        ]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            "team_code",
            "name",
            "academic_year",
            "status",
            "selection_round",
            "annual_average",
            "assignment_validated_at",
            "assignment_validated_by",
            "created_at",
            "updated_at",
            "dissolved_at",
        ]


class TeamDetailSerializer(serializers.ModelSerializer):
    participants = TeamParticipantSerializer(many=True, read_only=True)
    active_leader = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    active_supervisors = serializers.SerializerMethodField()
    pending_invitations = serializers.SerializerMethodField()
    active_student_count = serializers.SerializerMethodField()
    selected_subject_id = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "team_code",
            "name",
            "academic_year",
            "status",
            "selection_round",
            "annual_average",
            "selected_subject_id",
            "active_student_count",
            "assignment_validated_at",
            "assignment_validated_by",
            "active_leader",
            "active_members",
            "active_supervisors",
            "pending_invitations",
            "participants",
            "created_at",
            "updated_at",
            "dissolved_at",
        ]

    def _serialize_participants(self, obj, *, role=None, status=None):
        queryset = obj.participants.select_related("user")
        if role:
            queryset = queryset.filter(role=role)
        if status:
            queryset = queryset.filter(status=status)
        return TeamParticipantSerializer(queryset.order_by("created_at"), many=True).data

    def get_active_leader(self, obj):
        participant = obj.participants.select_related("user").filter(
            role=TeamParticipant.Role.LEADER,
            status=TeamParticipant.Status.ACTIVE,
        ).first()
        return TeamParticipantSerializer(participant).data if participant else None

    def get_active_members(self, obj):
        return self._serialize_participants(
            obj,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.ACTIVE,
        )

    def get_active_supervisors(self, obj):
        return self._serialize_participants(
            obj,
            role=TeamParticipant.Role.SUPERVISOR,
            status=TeamParticipant.Status.ACTIVE,
        )

    def get_pending_invitations(self, obj):
        return self._serialize_participants(
            obj,
            role=TeamParticipant.Role.MEMBER,
            status=TeamParticipant.Status.PENDING,
        )

    def get_active_student_count(self, obj):
        return obj.participants.filter(
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        ).count()

    def get_selected_subject_id(self, obj):
        subject = getattr(obj, "selected_subject", None)
        return subject.id if subject else None


class InviteStudentSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(required=False)
    matricule = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate(self, attrs):
        identifiers = [attrs.get("student_id"), attrs.get("matricule"), attrs.get("email")]
        if len([value for value in identifiers if value]) != 1:
            raise serializers.ValidationError("Provide exactly one of student_id, matricule, or email.")
        return attrs

    def get_student(self):
        attrs = self.validated_data
        queryset = User.objects.all()
        if attrs.get("student_id"):
            return queryset.filter(id=attrs["student_id"]).first()
        if attrs.get("matricule"):
            return queryset.filter(matricule__iexact=attrs["matricule"]).first()
        return queryset.filter(email__iexact=attrs["email"]).first()


class RemoveMemberSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()

    def get_student(self):
        return User.objects.filter(id=self.validated_data["student_id"]).first()


class AdminRemoveMemberSerializer(RemoveMemberSerializer):
    new_leader_id = serializers.IntegerField(required=False, allow_null=True)
    dissolve_if_needed = serializers.BooleanField(required=False, default=False)

    def get_new_leader(self):
        new_leader_id = self.validated_data.get("new_leader_id")
        if not new_leader_id:
            return None
        return User.objects.filter(id=new_leader_id).first()


class TransferLeadershipSerializer(serializers.Serializer):
    new_leader_id = serializers.IntegerField()

    def get_new_leader(self):
        return User.objects.filter(id=self.validated_data["new_leader_id"]).first()


class AddSupervisorSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def get_user(self):
        return User.objects.filter(id=self.validated_data["user_id"]).first()


class RemoveSupervisorSerializer(AddSupervisorSerializer):
    pass
