from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import StudentProfile, TeacherProfile, User

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
        "global_role",
        "is_active",
        "is_archived",
        "is_staff",
        "created_at",
    )
    list_filter = ("global_role", "is_active", "is_archived", "is_staff")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "matricule",
                    "first_name",
                    "last_name",
                    "global_role",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_archived",
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
                    "global_role",
                    "is_active",
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
