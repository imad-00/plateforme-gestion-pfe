from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import (
    AdministrativeStaffProfile,
    ExternalSupervisorProfile,
    PasswordResetOTP,
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
        "created_at",
    )
    list_filter = ("business_identity", "account_status")

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
            "Groups & Permissions",
            {
                "fields": (
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
        "speciality",
        "annual_average",
        "created_at",
    )
    list_filter = ("academic_year", "speciality")
    search_fields = (
        "user__matricule",
        "user__email",
        "user__first_name",
        "user__last_name",
        "speciality",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "grade", "department", "created_at")
    list_filter = ("grade", "department")
    search_fields = (
        "user__matricule",
        "user__email",
        "user__first_name",
        "user__last_name",
        "grade",
        "department",
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
    list_display = ("id", "user", "organization", "job_title", "expertise_area", "created_at")
    list_filter = ("organization", "job_title", "expertise_area")
    search_fields = ("user__matricule", "user__email", "organization", "job_title", "expertise_area")
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


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "expires_at",
        "verified_at",
        "consumed_at",
        "created_at",
    )
    list_filter = ("verified_at", "consumed_at")
    search_fields = ("user__matricule", "user__email", "verification_token")
    ordering = ("-created_at",)
    readonly_fields = (
        "otp_code_hash",
        "verification_token",
        "created_at",
        "updated_at",
    )
