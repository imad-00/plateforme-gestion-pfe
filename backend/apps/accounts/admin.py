from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import (
    AdministrativeStaffProfile,
    ExternalSupervisorProfile,
    PlatformAccessGrant,
    StudentProfile,
    TeacherProfile,
    User,
)

admin.site.site_header = "PFE Management Administration"
admin.site.site_title = "PFE Admin"
admin.site.index_title = "PFE Platform Administration"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("id",)
    list_display = (
        "id",
        "matricule",
        "email",
        "first_name",
        "last_name",
        "business_identity",
        "account_status",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    list_filter = ("business_identity", "account_status", "is_staff", "is_superuser")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "matricule",
                    "first_name",
                    "last_name",
                    "business_identity",
                    "account_status",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_archived",
                    "global_role",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "matricule",
                    "email",
                    "password1",
                    "password2",
                    "business_identity",
                    "account_status",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    search_fields = ("email", "matricule", "first_name", "last_name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "academic_year",
        "specialite",
        "moyenne_generale",
        "created_at",
    )
    list_filter = ("academic_year", "specialite")
    search_fields = (
        "user__matricule",
        "user__email",
        "user__first_name",
        "user__last_name",
        "specialite",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "grade", "departement", "created_at")
    list_filter = ("grade", "departement")
    search_fields = (
        "user__matricule",
        "user__email",
        "user__first_name",
        "user__last_name",
        "grade",
        "departement",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AdministrativeStaffProfile)
class AdministrativeStaffProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "position", "department", "created_at")
    list_filter = ("position", "department")
    search_fields = ("user__matricule", "user__email", "position", "department")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExternalSupervisorProfile)
class ExternalSupervisorProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "organization", "job_title", "created_at")
    list_filter = ("organization", "job_title")
    search_fields = ("user__matricule", "user__email", "organization", "job_title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlatformAccessGrant)
class PlatformAccessGrantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "access_level",
        "granted_by",
        "granted_at",
        "revoked_at",
    )
    list_filter = ("access_level", "revoked_at")
    search_fields = ("user__matricule", "user__email", "granted_by__matricule")
    ordering = ("-granted_at",)
    readonly_fields = ("created_at", "updated_at")
