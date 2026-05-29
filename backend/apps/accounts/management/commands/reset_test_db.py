from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import AcademicYear
from apps.accounts.models import PlatformAccessGrant, User
from apps.assignments.models import Appeal, WishItem, WishList
from apps.campaigns.models import CampaignPhase
from apps.defenses.models import Defense, DefenseJuryAssignment
from apps.deliverables.models import DeliverableFile, DeliverableFileComment
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject

# Reuse shared constants from the seed command so credentials stay in sync.
from apps.accounts.management.commands.seed import _PASSWORD, _PHASE_ORDER

_SUPER_ADMIN_MATRICULE = "SADM001"

_SUPER_ADMIN = {
    "matricule": _SUPER_ADMIN_MATRICULE,
    "email": "superadmin@example.com",
    "first_name": "Super",
    "last_name": "Admin",
    "business_identity": User.BusinessIdentity.ADMINISTRATIVE_STAFF,
}


class Command(BaseCommand):
    help = (
        "Reset the database to a clean testing baseline. "
        "Deletes all campaign data and every user except the super admin, "
        "then ensures one SUPER_ADMIN + an ACTIVE AcademicYear + CampaignPhases exist. "
        "Requires DEBUG=True or --confirm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Bypass the DEBUG safety check and actually run the reset.",
        )
        parser.add_argument(
            "--phase",
            default=CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
            choices=[p.value for p in CampaignPhase.PhaseType],
            metavar="PHASE",
            help=(
                "Campaign phase to mark as currently open. "
                f"Choices: {', '.join(p.value for p in CampaignPhase.PhaseType)}. "
                "Default: SUBJECT_MANAGEMENT."
            ),
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["confirm"]:
            raise CommandError(
                "Safety check failed.\n"
                "This command will permanently delete:\n"
                "  • ALL campaign data (deliverables, defenses, appeals, wishlists, teams, subjects)\n"
                "  • ALL users except SADM001 and their platform access grants\n"
                "\n"
                "Run with --confirm to proceed, or set DEBUG=True in settings."
            )

        open_phase = options["phase"]

        self.stdout.write(self.style.WARNING(
            "\nWARNING — the following will be permanently deleted:\n"
            "  DeliverableFileComments, DeliverableFiles\n"
            "  DefenseJuryAssignments, Defenses\n"
            "  Appeals, WishItems, WishLists\n"
            "  TeamParticipants, Teams\n"
            "  Subjects\n"
            "  PlatformAccessGrants (non-SADM001)\n"
            f"  All Users except {_SUPER_ADMIN_MATRICULE}\n"
        ))

        with transaction.atomic():
            self._delete_campaign_data()
            self._delete_users()

            self.stdout.write(self.style.MIGRATE_HEADING("\nEnsuring super admin…"))
            self._ensure_super_admin()

            self.stdout.write(self.style.MIGRATE_HEADING("\nEnsuring academic year…"))
            year = self._ensure_academic_year()

            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\nEnsuring campaign phases (open: {open_phase})…")
            )
            self._ensure_phases(year, open_phase)

        self.stdout.write("\n" + self.style.SUCCESS("Reset complete."))

    # ── deletion ───────────────────────────────────────────────────────────────

    def _delete_campaign_data(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\nDeleting campaign data…"))

        # Deletion order is strictly FK-safe. Each step removes rows that would
        # block the next step via PROTECT constraints.
        #
        # PROTECT graph (child → parent that blocks parent deletion):
        #   DeliverableFileComment → DeliverableFile, User
        #   DeliverableFile        → Team, User
        #   DefenseJuryAssignment  → User  (Defense cascades to it, but User PROTECT
        #                                   means we must clear it before deleting users)
        #   Defense                → Team  (PROTECT — must precede Team deletion)
        #   Appeal                 → User  (PROTECT — must precede User deletion)
        #   WishItem               → Subject (PROTECT — must precede Subject deletion)
        #   WishList               → User  (PROTECT — must precede User deletion)
        #   TeamParticipant        → User  (PROTECT — must precede User deletion)
        #   Team                   → User via assignment_validated_by (PROTECT)
        #   Subject                → User via proposed_by / reviewed_by (PROTECT)

        steps = [
            ("DeliverableFileComment", DeliverableFileComment),
            ("DeliverableFile",        DeliverableFile),
            ("DefenseJuryAssignment",  DefenseJuryAssignment),
            ("Defense",                Defense),
            ("Appeal",                 Appeal),
            ("WishItem",               WishItem),
            ("WishList",               WishList),
            ("TeamParticipant",        TeamParticipant),
            ("Team",                   Team),
            ("Subject",                Subject),
        ]

        for label, model_cls in steps:
            count, _ = model_cls.objects.all().delete()
            if count:
                self.stdout.write(f"  deleted {count:>6}  {label}")
            else:
                self.stdout.write(f"  skipped         {label} (0 rows)")

    def _delete_users(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\nDeleting users…"))

        # PlatformAccessGrant.user is PROTECT, so grants must be deleted before
        # their users, not the other way around.
        grant_count, _ = (
            PlatformAccessGrant.objects
            .exclude(user__matricule=_SUPER_ADMIN_MATRICULE)
            .delete()
        )
        if grant_count:
            self.stdout.write(f"  deleted {grant_count:>6}  PlatformAccessGrant (non-super-admin)")
        else:
            self.stdout.write("  skipped         PlatformAccessGrant (0 rows)")

        # Profiles (StudentProfile, TeacherProfile, etc.) and PasswordResetOTPs
        # all have on_delete=CASCADE to User, so they are auto-deleted here.
        user_count, _ = User.objects.exclude(matricule=_SUPER_ADMIN_MATRICULE).delete()
        if user_count:
            self.stdout.write(f"  deleted {user_count:>6}  User + cascaded profiles/OTPs")
        else:
            self.stdout.write("  skipped         User (0 rows)")

    # ── ensure helpers (mirrored from seed command) ────────────────────────────

    def _ensure_super_admin(self):
        if User.objects.filter(matricule=_SUPER_ADMIN_MATRICULE).exists():
            user = User.objects.get(matricule=_SUPER_ADMIN_MATRICULE)
            self.stdout.write(f"  keep   user  {_SUPER_ADMIN['email']} ({_SUPER_ADMIN_MATRICULE})")
        else:
            user = User.objects.create_user(
                matricule=_SUPER_ADMIN["matricule"],
                email=_SUPER_ADMIN["email"],
                password=_PASSWORD,
                first_name=_SUPER_ADMIN["first_name"],
                last_name=_SUPER_ADMIN["last_name"],
                business_identity=_SUPER_ADMIN["business_identity"],
                account_status=User.AccountStatus.ACTIVE,
            )
            self.stdout.write(
                self.style.SUCCESS(f"  create user  {_SUPER_ADMIN['email']} ({_SUPER_ADMIN_MATRICULE})")
            )

        grant, created = PlatformAccessGrant.objects.get_or_create(
            user=user,
            revoked_at=None,
            defaults={"access_level": PlatformAccessGrant.AccessLevel.SUPER_ADMIN},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"  create grant SUPER_ADMIN → {_SUPER_ADMIN_MATRICULE}")
            )
        else:
            self.stdout.write(f"  keep   grant {grant.access_level} → {_SUPER_ADMIN_MATRICULE}")

        return user

    def _ensure_academic_year(self):
        year_str = "2024-2025"

        # Close any other ACTIVE year first so the single-active-year DB
        # constraint is never violated during update_or_create.
        closed = (
            AcademicYear.objects
            .exclude(year=year_str)
            .filter(status=AcademicYear.Status.ACTIVE)
            .update(status=AcademicYear.Status.CLOSED)
        )
        if closed:
            self.stdout.write(f"  closed {closed} other active year(s)")

        year, created = AcademicYear.objects.update_or_create(
            year=year_str,
            defaults={
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 7, 31),
                "status": AcademicYear.Status.ACTIVE,
                "wishlist_size": 5,
            },
        )
        verb = "create" if created else "update"
        self.stdout.write(self.style.SUCCESS(f"  {verb} AcademicYear {year_str} (ACTIVE)"))
        return year

    def _ensure_phases(self, year, open_phase):
        now = timezone.now()
        open_idx = _PHASE_ORDER.index(open_phase)
        # Anchor so that _PHASE_ORDER[open_idx].start_at == now - 1 day.
        phase_zero_start = now - timedelta(days=1) - timedelta(days=open_idx * 14)

        for i, phase_type in enumerate(_PHASE_ORDER):
            start_at = phase_zero_start + timedelta(days=i * 14)
            if i < open_idx:
                end_at = start_at + timedelta(days=14)
            elif i == open_idx:
                end_at = now + timedelta(days=30)
            else:
                end_at = None  # future phases have no end date yet

            _, created = CampaignPhase.objects.update_or_create(
                academic_year=year,
                phase_type=phase_type,
                defaults={
                    "start_at": start_at,
                    "end_at": end_at,
                    "display_order": i + 1,
                    "is_archived": False,
                },
            )
            if i < open_idx:
                marker = "past  "
            elif i == open_idx:
                marker = "open  "
            else:
                marker = "future"
            verb = "create" if created else "update"
            line = f"  {verb} [{marker}] {phase_type}"
            self.stdout.write(self.style.SUCCESS(line) if created else line)
