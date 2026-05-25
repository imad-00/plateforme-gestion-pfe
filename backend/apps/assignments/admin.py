from django.contrib import admin

from apps.assignments.models import Appeal, WishItem, WishList


class WishItemInline(admin.TabularInline):
    model = WishItem
    extra = 0
    readonly_fields = ["wishitem_id"]


@admin.register(WishList)
class WishListAdmin(admin.ModelAdmin):
    list_display = ["wishlist_id", "team", "selection_round", "status", "submitted_by", "submitted_at"]
    list_filter = ["selection_round", "status", "academic_year"]
    search_fields = ["team__team_code", "team__name", "submitted_by__matricule", "submitted_by__email"]
    ordering = ["-created_at"]
    readonly_fields = ["wishlist_id", "created_at", "updated_at"]
    inlines = [WishItemInline]


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ["appeal_id", "team", "status", "submitted_by", "reviewed_by", "submitted_at", "resolved_at"]
    list_filter = ["status"]
    search_fields = ["team__team_code", "team__name", "submitted_by__matricule", "submitted_by__email"]
    ordering = ["-submitted_at"]
    readonly_fields = ["appeal_id", "created_at", "updated_at"]
