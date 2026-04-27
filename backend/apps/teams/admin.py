from django.contrib import admin

from apps.teams.models import Team, TeamParticipant


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "team_code",
        "name",
        "academic_year",
        "status",
        "selection_round",
        "created_at",
        "dissolved_at",
    )
    list_filter = ("status", "selection_round", "academic_year")
    search_fields = ("team_code", "name")
    ordering = ("-created_at",)
    readonly_fields = ("team_code", "created_at", "updated_at", "dissolved_at")


@admin.register(TeamParticipant)
class TeamParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "participation_id",
        "team",
        "user",
        "role",
        "status",
        "joined_at",
        "ended_at",
    )
    list_filter = ("role", "status")
    search_fields = ("team__team_code", "team__name", "user__matricule", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("participation_id", "created_at", "updated_at")
