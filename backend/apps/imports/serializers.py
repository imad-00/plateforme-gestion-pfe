from rest_framework import serializers

from apps.imports.models import UserImportBatch


class UserImportPreviewSerializer(serializers.Serializer):
    file = serializers.FileField()
    import_type = serializers.ChoiceField(choices=UserImportBatch.ImportType.choices)


class UserImportConfirmSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField()
    confirm = serializers.BooleanField()
    allow_partial = serializers.BooleanField(required=False, default=False)


class UserImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserImportBatch
        fields = [
            "id",
            "import_type",
            "status",
            "original_filename",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "errors",
            "warnings",
            "created_count",
            "skipped_count",
            "created_at",
            "completed_at",
        ]
