from rest_framework import serializers

from apps.audit.models import AdminActionLog


class AdminActionActorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    matricule = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


class AdminActionLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AdminActionLog
        fields = [
            "id",
            "actor",
            "action_type",
            "target_model",
            "target_id",
            "target_repr",
            "occurred_at",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        ]

    def get_actor(self, obj):
        return {
            "id": obj.actor_id,
            "matricule": obj.actor.matricule,
            "email": obj.actor.email,
            "full_name": obj.actor.full_name,
        }
