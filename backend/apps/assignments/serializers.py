from rest_framework import serializers

from apps.assignments.models import Appeal, WishItem, WishList
from apps.teams.models import Team
from apps.teams.serializers import TeamSerializer
from apps.topics.models import Subject
from apps.topics.serializers import PublicSubjectSerializer


class WishItemInputSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    rank = serializers.IntegerField(min_value=1)


class WishItemSerializer(serializers.ModelSerializer):
    subject = PublicSubjectSerializer(read_only=True)

    class Meta:
        model = WishItem
        fields = ["wishitem_id", "subject", "rank"]


class SubmitWishListSerializer(serializers.Serializer):
    selection_round = serializers.ChoiceField(choices=Team.SelectionRound.choices)
    items = WishItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Wishlist cannot be empty.")
        return value


class WishListSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = WishList
        fields = [
            "wishlist_id",
            "team",
            "selection_round",
            "status",
            "submitted_by",
            "submitted_at",
            "item_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.items.count()


class WishListDetailSerializer(WishListSerializer):
    items = WishItemSerializer(many=True, read_only=True)

    class Meta(WishListSerializer.Meta):
        fields = WishListSerializer.Meta.fields + ["items"]


class AppealCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class AppealSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Appeal
        fields = [
            "appeal_id",
            "team",
            "reason",
            "status",
            "submitted_by",
            "reviewed_by",
            "submitted_at",
            "resolved_at",
            "admin_comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminAppealReviewSerializer(serializers.Serializer):
    admin_comment = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class AssignmentRoundSerializer(serializers.Serializer):
    selection_round = serializers.ChoiceField(choices=Team.SelectionRound.choices)
    seed = serializers.IntegerField(required=False, allow_null=True)


class ManualAssignmentSerializer(serializers.Serializer):
    team_code = serializers.CharField()
    subject_id = serializers.IntegerField()

    def get_team(self):
        return Team.objects.filter(pk=self.validated_data["team_code"]).first()

    def get_subject(self):
        return Subject.objects.filter(pk=self.validated_data["subject_id"]).first()
