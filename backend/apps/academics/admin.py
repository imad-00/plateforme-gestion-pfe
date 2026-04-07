from django.contrib import admin

from apps.academics.models import AcademicYear


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "year",
        "is_active",
        "is_archived",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "is_archived")
    search_fields = ("year",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
