from rest_framework import serializers

from apps.deliverables.models import DeliverableFile, DeliverableFileComment
from apps.teams.models import Team, TeamParticipant
from apps.teams.serializers import TeamUserSummarySerializer


class DeliverableTeamSummarySerializer(serializers.ModelSerializer):
    selected_subject_id = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["team_code", "name", "academic_year", "status", "selected_subject_id"]

    def get_selected_subject_id(self, obj):
        subject = getattr(obj, "selected_subject", None)
        return subject.id if subject else None


class DeliverableFileSerializer(serializers.ModelSerializer):
    team = DeliverableTeamSummarySerializer(read_only=True)
    uploaded_by = TeamUserSummarySerializer(read_only=True)
    reviewed_by = TeamUserSummarySerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = DeliverableFile
        fields = [
            "id",
            "team",
            "file",
            "file_url",
            "original_filename",
            "file_size",
            "content_type",
            "uploaded_by",
            "uploaded_at",
            "comment",
            "review_status",
            "reviewed_by",
            "reviewed_at",
            "review_comment",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        try:
            return obj.file.url
        except Exception:
            return ""

    def get_comments(self, obj):
        comments = obj.comments.select_related("author")
        return DeliverableFileCommentSerializer(comments, many=True).data


class DeliverableFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    comment = serializers.CharField(required=False, allow_blank=True)


class DeliverableFileReviewSerializer(serializers.Serializer):
    review_status = serializers.ChoiceField(
        choices=[
            DeliverableFile.ReviewStatus.ACCEPTED,
            DeliverableFile.ReviewStatus.NEEDS_REVISION,
            DeliverableFile.ReviewStatus.REJECTED,
        ]
    )
    review_comment = serializers.CharField(required=False, allow_blank=True)


class DeliverableFileCommentSerializer(serializers.ModelSerializer):
    author = TeamUserSummarySerializer(read_only=True)

    class Meta:
        model = DeliverableFileComment
        fields = ["id", "author", "text", "created_at", "updated_at"]
        read_only_fields = fields


class DeliverableFileCommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField()

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        return value.strip()


class SupervisedTeamSerializer(serializers.ModelSerializer):
    selected_subject_id = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    members_summary = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "team_code",
            "name",
            "academic_year",
            "status",
            "selected_subject_id",
            "files_count",
            "members_summary",
        ]

    def get_selected_subject_id(self, obj):
        subject = getattr(obj, "selected_subject", None)
        return subject.id if subject else None

    def get_files_count(self, obj):
        return obj.deliverable_files.count()

    def get_members_summary(self, obj):
        participants = obj.participants.select_related("user").filter(
            role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            status=TeamParticipant.Status.ACTIVE,
        )
        return TeamUserSummarySerializer([participant.user for participant in participants], many=True).data
