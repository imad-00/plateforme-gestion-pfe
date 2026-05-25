from django.contrib import admin

from apps.topics.models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject_code",
        "title",
        "subject_type",
        "status",
        "proposed_by",
        "academic_year",
        "created_at",
    )
    list_filter = ("subject_type", "status", "academic_year")
    search_fields = ("subject_code", "title", "proposed_by__matricule", "proposed_by__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "submitted_at", "reviewed_at")
