from django.db import migrations
from django.utils import timezone


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    PlatformAccessGrant = apps.get_model("accounts", "PlatformAccessGrant")

    now = timezone.now()

    for user in User.objects.all().iterator():
        if user.is_archived:
            account_status = "ARCHIVED"
        elif user.is_active:
            account_status = "ACTIVE"
        else:
            account_status = "SUSPENDED"

        if user.global_role == "TEACHER":
            business_identity = "TEACHER"
        elif user.global_role in {"ADMIN", "SUPER_ADMIN"}:
            business_identity = "ADMINISTRATIVE_STAFF"
        else:
            business_identity = "STUDENT"

        user.account_status = account_status
        user.business_identity = business_identity

        if user.global_role in {"ADMIN", "SUPER_ADMIN"}:
            user.is_staff = True
            if user.global_role == "SUPER_ADMIN":
                user.is_superuser = True

        user.save(
            update_fields=[
                "account_status",
                "business_identity",
                "is_staff",
                "is_superuser",
                "updated_at",
            ]
        )

    for user in User.objects.filter(global_role__in=["ADMIN", "SUPER_ADMIN"]):
        if PlatformAccessGrant.objects.filter(user_id=user.id, revoked_at__isnull=True).exists():
            continue

        level = "SUPER_ADMIN" if user.global_role == "SUPER_ADMIN" else "ADMIN"
        PlatformAccessGrant.objects.create(
            user_id=user.id,
            access_level=level,
            granted_at=now,
        )


def noop_reverse(apps, schema_editor):
    # Sprint 4 introduces new identity/access structures; reverse data mapping is intentionally no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_administrativestaffprofile_externalsupervisorprofile_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
