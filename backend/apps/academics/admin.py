from django.contrib import admin

from apps.academics.models import AcademicYear


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "year",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("year",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
