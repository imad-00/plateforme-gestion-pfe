from django.contrib import admin

from apps.archives.models import AcademicYearLifecycleEvent


@admin.register(AcademicYearLifecycleEvent)
class AcademicYearLifecycleEventAdmin(admin.ModelAdmin):
    list_display = ("id", "academic_year", "event_type", "performed_by", "performed_at")
    list_filter = ("event_type", "academic_year")
    search_fields = ("academic_year__year", "performed_by__matricule", "performed_by__email", "reason")
    readonly_fields = (
        "academic_year",
        "event_type",
        "performed_by",
        "performed_at",
        "reason",
        "metadata",
        "created_at",
        "updated_at",
    )
