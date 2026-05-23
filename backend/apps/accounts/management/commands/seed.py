from django.core.management.base import BaseCommand

from apps.accounts.models import PlatformAccessGrant, StudentProfile, TeacherProfile, User

_PASSWORD = "Testpass123!"

_ACCOUNTS = [
    {
        "matricule": "STU001",
        "email": "student@example.com",
        "first_name": "Student",
        "last_name": "One",
        "business_identity": User.BusinessIdentity.STUDENT,
    },
    {
        "matricule": "TEA001",
        "email": "teacher@example.com",
        "first_name": "Teacher",
        "last_name": "One",
        "business_identity": User.BusinessIdentity.TEACHER,
    },
    {
        "matricule": "ADM001",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "One",
        "business_identity": User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        "access_level": PlatformAccessGrant.AccessLevel.ADMIN,
    },
    {
        "matricule": "SADM001",
        "email": "superadmin@example.com",
        "first_name": "Super",
        "last_name": "Admin",
        "business_identity": User.BusinessIdentity.ADMINISTRATIVE_STAFF,
        "access_level": PlatformAccessGrant.AccessLevel.SUPER_ADMIN,
    },
]


class Command(BaseCommand):
    help = "Seed demo accounts for local development (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo accounts…\n"))
        for spec in _ACCOUNTS:
            self._ensure_account(spec)
        self.stdout.write("\n" + self.style.SUCCESS("Done."))

    # ── internals ──────────────────────────────────────────────────────────────

    def _ensure_account(self, spec):
        matricule = spec["matricule"]
        email = spec["email"]
        identity = spec["business_identity"]
        access_level = spec.get("access_level")

        # ── User ──
        if User.objects.filter(matricule=matricule).exists():
            user = User.objects.get(matricule=matricule)
            self.stdout.write(f"  skip   user  {email} ({matricule})")
        else:
            user = User.objects.create_user(
                matricule=matricule,
                email=email,
                password=_PASSWORD,
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                business_identity=identity,
                account_status=User.AccountStatus.ACTIVE,
            )
            self.stdout.write(self.style.SUCCESS(f"  create user  {email} ({matricule})"))

        # ── Role-specific profile ──
        if identity == User.BusinessIdentity.STUDENT:
            _, created = StudentProfile.objects.get_or_create(user=user)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  create StudentProfile → {matricule}"))

        elif identity == User.BusinessIdentity.TEACHER:
            _, created = TeacherProfile.objects.get_or_create(user=user)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  create TeacherProfile → {matricule}"))

        # ── PlatformAccessGrant ──
        if access_level:
            grant, created = PlatformAccessGrant.objects.get_or_create(
                user=user,
                revoked_at=None,
                defaults={"access_level": access_level},
            )
            if created:
                # save() already called full_clean() + refresh_platform_flags()
                self.stdout.write(
                    self.style.SUCCESS(f"  create grant {access_level} → {matricule}")
                )
            else:
                self.stdout.write(f"  skip   grant {grant.access_level} → {matricule}")
