from django.contrib import admin

from apps.campaigns.models import CampaignPhase


@admin.register(CampaignPhase)
class CampaignPhaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "academic_year",
        "phase_type",
        "display_order",
        "start_at",
        "end_at",
        "is_archived",
    )
    list_filter = ("phase_type", "is_archived", "academic_year")
    search_fields = ("academic_year__year", "phase_type")
    ordering = ("academic_year", "display_order", "start_at")
    readonly_fields = ("created_at", "updated_at")
