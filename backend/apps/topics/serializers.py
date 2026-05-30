from django.db import transaction
from django.utils import timezone
from uuid import uuid4
from rest_framework import serializers

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.topics.models import Subject


class SubjectTeacherSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "matricule", "first_name", "last_name", "email"]


class SubjectAcademicYearSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "year", "status"]


class TeacherSubjectListSerializer(serializers.ModelSerializer):
    academic_year = SubjectAcademicYearSummarySerializer(read_only=True)
    attachment_key = serializers.CharField(source="attachment_url", read_only=True)
    attachment_original_name = serializers.SerializerMethodField()
    attachment_mime_type = serializers.SerializerMethodField()
    attachment_size_bytes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id",
            "subject_code",
            "title",
            "description",
            "subject_type",
            "attachment_url",
            "attachment_key",
            "attachment_original_name",
            "attachment_mime_type",
            "attachment_size_bytes",
            "status",
            "academic_year",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "assigned_at",
            "assigned_to_team",
            "created_at",
            "updated_at",
        ]

    def get_attachment_original_name(self, obj):
        return (obj.attachment_metadata or {}).get("original_name", "")

    def get_attachment_mime_type(self, obj):
        return (obj.attachment_metadata or {}).get("mime_type", "")

    def get_attachment_size_bytes(self, obj):
        return (obj.attachment_metadata or {}).get("size_bytes")


class TeacherSubjectWriteSerializer(serializers.ModelSerializer):
    attachment_key = serializers.CharField(required=False, allow_blank=True, write_only=True)
    attachment_original_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    attachment_mime_type = serializers.CharField(required=False, allow_blank=True, write_only=True)
    attachment_size_bytes = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Subject
        fields = [
            "subject_code",
            "title",
            "description",
            "subject_type",
            "attachment_url",
            "attachment_key",
            "attachment_original_name",
            "attachment_mime_type",
            "attachment_size_bytes",
            "academic_year",
        ]
        extra_kwargs = {"academic_year": {"required": False}}

    def _get_active_academic_year(self):
        return AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()

    def validate_academic_year(self, value):
        if value.status != AcademicYear.Status.ACTIVE:
            raise serializers.ValidationError("Subject must be linked to the active academic year.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if getattr(user, "business_identity", None) != User.BusinessIdentity.TEACHER:
            raise serializers.ValidationError("Only TEACHER users can create or update personal subjects.")

        active_year = self._get_active_academic_year()
        if active_year is None:
            raise serializers.ValidationError(
                {"academic_year": "No active academic year is configured."}
            )
        CampaignPhaseService.require_open(active_year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)

        instance = getattr(self, "instance", None)
        if instance is not None and not instance.is_editable_by_teacher:
            raise serializers.ValidationError(
                {"status": "Only DRAFT or REJECTED subjects can be edited by teacher."}
            )
        if instance is not None and instance.academic_year_id != active_year.id:
            raise serializers.ValidationError(
                {"academic_year": "Subject belongs to a past academic year and cannot be edited."}
            )

        provided_year = attrs.get("academic_year")
        if provided_year is not None and provided_year.id != active_year.id:
            raise serializers.ValidationError(
                {"academic_year": "Only the current active academic year can be used."}
            )

        if attrs.get("attachment_key") and not attrs.get("attachment_url"):
            attrs["attachment_url"] = attrs["attachment_key"]
        attrs["attachment_metadata"] = {
            "original_name": attrs.get("attachment_original_name", ""),
            "mime_type": attrs.get("attachment_mime_type", ""),
            "size_bytes": attrs.get("attachment_size_bytes"),
        }
        attrs.pop("attachment_key", None)
        attrs.pop("attachment_original_name", None)
        attrs.pop("attachment_mime_type", None)
        attrs.pop("attachment_size_bytes", None)

        attrs["academic_year"] = active_year

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if not validated_data.get("subject_code"):
            validated_data["subject_code"] = f"SUB-{uuid4().hex[:10].upper()}"
        return Subject.objects.create(
            proposed_by=user,
            status=Subject.Status.DRAFT,
            rejection_reason="",
            **validated_data,
        )


class AdminSubjectListSerializer(serializers.ModelSerializer):
    proposed_by = SubjectTeacherSummarySerializer(read_only=True)
    reviewed_by = SubjectTeacherSummarySerializer(read_only=True)
    academic_year = SubjectAcademicYearSummarySerializer(read_only=True)
    attachment_key = serializers.CharField(source="attachment_url", read_only=True)
    attachment_original_name = serializers.SerializerMethodField()
    attachment_mime_type = serializers.SerializerMethodField()
    attachment_size_bytes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id",
            "subject_code",
            "title",
            "description",
            "subject_type",
            "attachment_url",
            "attachment_key",
            "attachment_original_name",
            "attachment_mime_type",
            "attachment_size_bytes",
            "status",
            "proposed_by",
            "academic_year",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "assigned_at",
            "assigned_to_team",
            "created_at",
            "updated_at",
        ]

    def get_attachment_original_name(self, obj):
        return (obj.attachment_metadata or {}).get("original_name", "")

    def get_attachment_mime_type(self, obj):
        return (obj.attachment_metadata or {}).get("mime_type", "")

    def get_attachment_size_bytes(self, obj):
        return (obj.attachment_metadata or {}).get("size_bytes")


class RejectSubjectSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class PublicSubjectSerializer(serializers.ModelSerializer):
    proposed_by = SubjectTeacherSummarySerializer(read_only=True)
    academic_year = SubjectAcademicYearSummarySerializer(read_only=True)
    attachment_key = serializers.CharField(source="attachment_url", read_only=True)

    class Meta:
        model = Subject
        fields = [
            "id",
            "subject_code",
            "title",
            "description",
            "subject_type",
            "attachment_url",
            "attachment_key",
            "proposed_by",
            "academic_year",
            "created_at",
            "updated_at",
        ]


class SubjectWorkflowService:
    """Simple explicit transition helpers used by teacher/admin actions."""

    @staticmethod
    def _ensure_active_academic_year_subject(subject: Subject):
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        if active_year is None:
            raise serializers.ValidationError(
                {"academic_year": "No active academic year is configured."}
            )
        if subject.academic_year_id != active_year.id or subject.academic_year.status == AcademicYear.Status.ARCHIVED:
            raise serializers.ValidationError(
                {"academic_year": "This subject is not in the current active academic year."}
            )
        CampaignPhaseService.require_open(subject.academic_year, CampaignPhase.PhaseType.SUBJECT_MANAGEMENT)

    @staticmethod
    @transaction.atomic
    def submit(subject: Subject):
        SubjectWorkflowService._ensure_active_academic_year_subject(subject)
        if subject.status != Subject.Status.DRAFT:
            raise serializers.ValidationError(
                {"status": "Only DRAFT subject can be submitted."}
            )

        subject.status = Subject.Status.SUBMITTED
        subject.submitted_at = timezone.now()
        subject.rejection_reason = ""
        subject.reviewed_at = None
        subject.reviewed_by = None
        subject.save(
            update_fields=[
                "status",
                "submitted_at",
                "rejection_reason",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_subject_event(
            subject,
            Notification.Type.SUBJECT_SUBMITTED,
            "Subject submitted",
            f"Your subject {subject.title} was submitted.",
            actor=subject.proposed_by,
        )
        NotificationService.notify_subject_pending_moderation(subject, actor=subject.proposed_by)
        return subject

    @staticmethod
    @transaction.atomic
    def resubmit(subject: Subject):
        SubjectWorkflowService._ensure_active_academic_year_subject(subject)
        if subject.status != Subject.Status.REJECTED:
            raise serializers.ValidationError(
                {"status": "Only REJECTED subject can be resubmitted."}
            )

        subject.status = Subject.Status.SUBMITTED
        subject.submitted_at = timezone.now()
        subject.rejection_reason = ""
        subject.reviewed_at = None
        subject.reviewed_by = None
        subject.save(
            update_fields=[
                "status",
                "submitted_at",
                "rejection_reason",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_subject_event(
            subject,
            Notification.Type.SUBJECT_RESUBMITTED,
            "Subject resubmitted",
            f"Your subject {subject.title} was resubmitted.",
            actor=subject.proposed_by,
        )
        NotificationService.notify_subject_pending_moderation(subject, actor=subject.proposed_by)
        return subject

    @staticmethod
    @transaction.atomic
    def approve(subject: Subject, reviewer: User):
        SubjectWorkflowService._ensure_active_academic_year_subject(subject)
        if subject.status != Subject.Status.SUBMITTED:
            raise serializers.ValidationError({"status": "Only SUBMITTED subject can be approved."})

        if subject.proposed_by_id == reviewer.id:
            raise serializers.ValidationError(
                {"detail": "You cannot approve your own subject."}
            )

        subject.status = Subject.Status.APPROVED
        subject.rejection_reason = ""
        subject.reviewed_at = timezone.now()
        subject.reviewed_by = reviewer
        subject.save(
            update_fields=[
                "status",
                "rejection_reason",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_subject_event(
            subject,
            Notification.Type.SUBJECT_APPROVED,
            "Subject approved",
            f"Your subject {subject.title} was approved.",
            actor=reviewer,
        )
        return subject

    @staticmethod
    @transaction.atomic
    def reject(subject: Subject, reviewer: User, reason: str):
        SubjectWorkflowService._ensure_active_academic_year_subject(subject)
        if subject.status != Subject.Status.SUBMITTED:
            raise serializers.ValidationError({"status": "Only SUBMITTED subject can be rejected."})

        if subject.proposed_by_id == reviewer.id:
            raise serializers.ValidationError(
                {"detail": "You cannot reject your own subject."}
            )

        clean_reason = reason.strip()
        if not clean_reason:
            raise serializers.ValidationError({"reason": "Rejection reason is required."})

        subject.status = Subject.Status.REJECTED
        subject.rejection_reason = clean_reason
        subject.reviewed_at = timezone.now()
        subject.reviewed_by = reviewer
        subject.save(
            update_fields=[
                "status",
                "rejection_reason",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )
        from apps.notifications.models import Notification
        from apps.notifications.services import NotificationService

        NotificationService.notify_subject_event(
            subject,
            Notification.Type.SUBJECT_REJECTED,
            "Subject rejected",
            f"Your subject {subject.title} was rejected.",
            actor=reviewer,
        )
        return subject

    @staticmethod
    @transaction.atomic
    def archive(subject: Subject, actor=None):
        SubjectWorkflowService._ensure_active_academic_year_subject(subject)
        if subject.status == Subject.Status.ARCHIVED:
            return subject

        subject.status = Subject.Status.ARCHIVED
        subject.save(update_fields=["status", "updated_at"])
        from apps.notifications.services import NotificationService

        NotificationService.notify_subject_archived(subject, actor=actor)
        return subject
