from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.academics.models import AcademicYear
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

    class Meta:
        model = Subject
        fields = [
            "id",
            "title",
            "description",
            "subject_type",
            "technologies",
            "keywords",
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
            "created_at",
            "updated_at",
        ]


class TeacherSubjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = [
            "title",
            "description",
            "subject_type",
            "technologies",
            "keywords",
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

        attrs["academic_year"] = active_year

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
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

    class Meta:
        model = Subject
        fields = [
            "id",
            "title",
            "description",
            "subject_type",
            "technologies",
            "keywords",
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
            "created_at",
            "updated_at",
        ]


class RejectSubjectSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class PublicSubjectSerializer(serializers.ModelSerializer):
    proposed_by = SubjectTeacherSummarySerializer(read_only=True)
    academic_year = SubjectAcademicYearSummarySerializer(read_only=True)

    class Meta:
        model = Subject
        fields = [
            "id",
            "title",
            "description",
            "subject_type",
            "technologies",
            "keywords",
            "attachment_key",
            "attachment_original_name",
            "attachment_mime_type",
            "attachment_size_bytes",
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
        return subject

    @staticmethod
    @transaction.atomic
    def archive(subject: Subject):
        if subject.status == Subject.Status.ARCHIVED:
            return subject

        subject.status = Subject.Status.ARCHIVED
        subject.save(update_fields=["status", "updated_at"])
        return subject
