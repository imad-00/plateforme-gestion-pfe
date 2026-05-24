from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.academics.models import AcademicYear
from apps.accounts.models import PlatformAccessGrant, StudentProfile, TeacherProfile, User
from apps.campaigns.models import CampaignPhase
from apps.topics.models import Subject

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
        "matricule": "STU002",
        "email": "student2@example.com",
        "first_name": "Alice",
        "last_name": "Martin",
        "business_identity": User.BusinessIdentity.STUDENT,
    },
    {
        "matricule": "STU003",
        "email": "student3@example.com",
        "first_name": "Yacine",
        "last_name": "Boudiaf",
        "business_identity": User.BusinessIdentity.STUDENT,
    },
    {
        "matricule": "STU004",
        "email": "student4@example.com",
        "first_name": "Sara",
        "last_name": "Hamdi",
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

_PHASE_ORDER = [
    CampaignPhase.PhaseType.CAMPAIGN_SETUP,
    CampaignPhase.PhaseType.SUBJECT_MANAGEMENT,
    CampaignPhase.PhaseType.TEAM_FORMATION,
    CampaignPhase.PhaseType.WISHLIST_1,
    CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_1,
    CampaignPhase.PhaseType.RESULTS_AND_APPEALS,
    CampaignPhase.PhaseType.WISHLIST_2,
    CampaignPhase.PhaseType.ASSIGNMENT_REVIEW_2,
    CampaignPhase.PhaseType.WORK_AND_SUPERVISION,
    CampaignPhase.PhaseType.DEFENSE_WINDOW,
    CampaignPhase.PhaseType.ARCHIVE,
]

_SUBJECT_SPECS = [
    {
        "subject_code": "SEED-001",
        "title": "Deep Learning for Medical Image Segmentation",
        "description": (
            "Research and implement deep learning models (U-Net variants) for automated "
            "segmentation of medical images (MRI, CT scans). Evaluate performance against "
            "standard clinical benchmarks and analyse model explainability."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-002",
        "title": "Real-Time Object Detection System for Embedded Hardware",
        "description": (
            "Build a real-time object detection pipeline using YOLOv8, deployable on "
            "embedded hardware (Jetson Nano / Raspberry Pi). Includes dataset collection, "
            "model training, quantisation, and a live demo application."
        ),
        "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-003",
        "title": "Federated Learning Framework for Privacy-Preserving Analytics",
        "description": (
            "Design and implement a federated learning system that trains models across "
            "distributed nodes without sharing raw data. Target a healthcare or financial "
            "use-case and benchmark against centralised training baselines."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-004",
        "title": "Smart Campus Energy Management Platform",
        "description": (
            "Develop an IoT-based energy monitoring and optimisation platform for campus "
            "buildings. Includes sensor data ingestion, anomaly detection with ML, and a "
            "real-time dashboard for facility managers."
        ),
        "subject_type": Subject.SubjectType.STARTUP_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-005",
        "title": "AI-Powered Code Review Assistant (VS Code Extension)",
        "description": (
            "Build a VS Code extension that uses an LLM to provide contextual code review "
            "suggestions, detect common bugs, and enforce team style guidelines. Includes "
            "a serverless backend for model inference."
        ),
        "subject_type": Subject.SubjectType.STARTUP_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-006",
        "title": "Multimodal Sentiment Analysis for Social-Media Content",
        "description": (
            "Build a pipeline that fuses text, image, and audio signals to classify "
            "sentiment in short-form social-media posts. Compare fusion strategies and "
            "evaluate on a multilingual benchmark including Algerian dialect."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-009",
        "title": "Open-Source LMS for Offline-First Schools",
        "description": (
            "Develop a lightweight learning management system that works fully offline "
            "on low-spec hardware and syncs to a central server when connectivity is "
            "available. Targets rural schools with intermittent internet access."
        ),
        "subject_type": Subject.SubjectType.STARTUP_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-010",
        "title": "Automated Vulnerability Scanner for REST APIs",
        "description": (
            "Design and implement a black-box scanner that detects common REST API "
            "vulnerabilities (OWASP API Top 10) through automated fuzzing and traffic "
            "analysis. Validated against a set of intentionally vulnerable lab services."
        ),
        "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-011",
        "title": "Graph Neural Networks for Citation-Network Analysis",
        "description": (
            "Apply GNN architectures (GCN, GAT, GraphSAGE) to tasks on academic citation "
            "graphs: link prediction, paper classification, and author disambiguation. "
            "Release a reproducible benchmark and pre-trained model weights."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-012",
        "title": "Peer-to-Peer Carpooling App for University Campuses",
        "description": (
            "Build a mobile-first carpooling platform tailored to university commuters. "
            "Features real-time ride matching, in-app chat, driver ratings, and a "
            "route optimisation engine. Monetisation via optional premium pass."
        ),
        "subject_type": Subject.SubjectType.STARTUP_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-013",
        "title": "Digital Twin for Industrial Equipment Monitoring",
        "description": (
            "Create a digital twin of a CNC machine or industrial pump using real sensor "
            "streams. The twin runs predictive-maintenance models and raises alerts before "
            "failure. Evaluated on a hardware-in-the-loop test bench."
        ),
        "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-014",
        "title": "Explainable Credit-Scoring Model for Microfinance",
        "description": (
            "Develop a machine-learning credit-scoring system for micro-loan applicants "
            "with limited credit history. Incorporate SHAP-based explanations so loan "
            "officers can justify decisions and regulators can audit outcomes."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-015",
        "title": "AR Navigation Assistant for University Buildings",
        "description": (
            "Build an augmented-reality indoor navigation app using ARCore/ARKit and a "
            "floor-plan graph. Guides students and visitors to rooms, labs, and offices "
            "via overlaid arrows without requiring GPS or dedicated beacons."
        ),
        "subject_type": Subject.SubjectType.STARTUP_PROJECT,
        "status": Subject.Status.APPROVED,
    },
    {
        "subject_code": "SEED-016",
        "title": "Blockchain-Based Academic Credential Verification",
        "description": (
            "Design a system for issuing and verifying academic credentials on a "
            "permissioned blockchain (Hyperledger Fabric). Includes an issuer portal, "
            "a student digital wallet, and an employer verification flow."
        ),
        "subject_type": Subject.SubjectType.APPLIED_PROJECT,
        "status": Subject.Status.SUBMITTED,
    },
    {
        "subject_code": "SEED-017",
        "title": "NLP for Arabic Legal Text Classification",
        "description": (
            "Investigate fine-tuning transformer models on an Algerian legal corpus for "
            "tasks including named-entity recognition, document classification, and clause "
            "extraction. Produce a public benchmark dataset."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.SUBMITTED,
    },
    {
        "subject_code": "SEED-018",
        "title": "Autonomous Drone Path Planning in Dynamic Environments",
        "description": (
            "Implement reinforcement-learning-based path planning algorithms for drones "
            "navigating obstacle-rich environments. Primary evaluation in Gazebo simulation; "
            "secondary validation on physical hardware."
        ),
        "subject_type": Subject.SubjectType.RESEARCH_PROJECT,
        "status": Subject.Status.DRAFT,
    },
]


class Command(BaseCommand):
    help = (
        "Seed demo data for local development (idempotent). "
        "Creates accounts, an academic year, campaign phases, and subjects."
    )

    def add_arguments(self, parser):
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
        open_phase = options["phase"]

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding demo accounts…\n"))
        users = {}
        for spec in _ACCOUNTS:
            users[spec["matricule"]] = self._ensure_account(spec)

        self.stdout.write(self.style.MIGRATE_HEADING("\nSeeding academic year…\n"))
        year = self._ensure_academic_year()

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"\nSeeding campaign phases (open: {open_phase})…\n")
        )
        self._ensure_phases(year, open_phase)

        self.stdout.write(self.style.MIGRATE_HEADING("\nSeeding subjects…\n"))
        self._ensure_subjects(year, teacher=users["TEA001"], admin=users["ADM001"])

        self.stdout.write("\n" + self.style.SUCCESS("Done."))

    # ── accounts ───────────────────────────────────────────────────────────────

    def _ensure_account(self, spec):
        matricule = spec["matricule"]
        email = spec["email"]
        identity = spec["business_identity"]
        access_level = spec.get("access_level")

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

        if identity == User.BusinessIdentity.STUDENT:
            _, created = StudentProfile.objects.get_or_create(user=user)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  create StudentProfile → {matricule}"))

        elif identity == User.BusinessIdentity.TEACHER:
            _, created = TeacherProfile.objects.get_or_create(user=user)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  create TeacherProfile → {matricule}"))

        if access_level:
            grant, created = PlatformAccessGrant.objects.get_or_create(
                user=user,
                revoked_at=None,
                defaults={"access_level": access_level},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  create grant {access_level} → {matricule}")
                )
            else:
                self.stdout.write(f"  skip   grant {grant.access_level} → {matricule}")

        return user

    # ── academic year ──────────────────────────────────────────────────────────

    def _ensure_academic_year(self):
        year_str = "2024-2025"

        # Close any other ACTIVE year before inserting/updating ours so the
        # single-active-year DB constraint is never violated.
        closed = AcademicYear.objects.exclude(year=year_str).filter(
            status=AcademicYear.Status.ACTIVE
        ).update(status=AcademicYear.Status.CLOSED)
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
        label = self.style.SUCCESS(f"  {verb} AcademicYear {year_str} (ACTIVE)")
        self.stdout.write(label)
        return year

    # ── campaign phases ────────────────────────────────────────────────────────

    def _ensure_phases(self, year, open_phase):
        now = timezone.now()
        open_idx = _PHASE_ORDER.index(open_phase)
        # Anchor so that phase[open_idx].start_at = now - 1 day
        phase_zero_start = now - timedelta(days=1) - timedelta(days=open_idx * 14)

        for i, phase_type in enumerate(_PHASE_ORDER):
            start_at = phase_zero_start + timedelta(days=i * 14)
            if i < open_idx:
                end_at = start_at + timedelta(days=14)
            elif i == open_idx:
                end_at = now + timedelta(days=30)
            else:
                end_at = None  # future phases have no end date yet

            phase, created = CampaignPhase.objects.update_or_create(
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

    # ── subjects ───────────────────────────────────────────────────────────────

    def _ensure_subjects(self, year, teacher, admin):
        now = timezone.now()
        for spec in _SUBJECT_SPECS:
            status = spec["status"]
            defaults = {
                "title": spec["title"],
                "description": spec["description"],
                "subject_type": spec["subject_type"],
                "status": status,
                "proposed_by": teacher,
                "academic_year": year,
            }
            if status == Subject.Status.APPROVED:
                defaults["submitted_at"] = now - timedelta(days=10)
                defaults["reviewed_at"] = now - timedelta(days=5)
                defaults["reviewed_by"] = admin
            elif status == Subject.Status.SUBMITTED:
                defaults["submitted_at"] = now - timedelta(days=2)

            subject, created = Subject.objects.get_or_create(
                subject_code=spec["subject_code"],
                defaults=defaults,
            )
            verb = "create" if created else "skip  "
            title_excerpt = spec["title"][:52]
            line = f"  {verb} [{status:<9}] {spec['subject_code']} – {title_excerpt}"
            self.stdout.write(self.style.SUCCESS(line) if created else line)
