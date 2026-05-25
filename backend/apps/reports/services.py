import csv
import io
from decimal import Decimal

from django.db.models import F, Prefetch
from django.http import HttpResponse

from apps.accounts.models import StudentProfile
from apps.defenses.models import Defense, DefenseJuryAssignment
from apps.teams.models import Team, TeamParticipant


class ReportService:
    DEFENSE_REPORT_COLUMNS = [
        "defense_id",
        "defense_status",
        "team_code",
        "team_name",
        "subject_title",
        "subject_type",
        "supervisors",
        "jury_president",
        "jury_examiners",
        "jury_guests",
        "scheduled_at",
        "location",
        "final_grade",
        "deliberation",
        "pv_uploaded_at",
        "pv_uploaded_by",
        "pv_file_url_or_name",
    ]
    TEAM_ASSIGNMENT_REPORT_COLUMNS = [
        "team_code",
        "team_name",
        "team_status",
        "selection_round",
        "annual_average",
        "students",
        "leader",
        "supervisors",
        "subject_title",
        "subject_type",
        "subject_status",
        "subject_proposed_by",
        "assignment_status",
    ]
    STUDENT_RESULTS_REPORT_COLUMNS = [
        "student_matricule",
        "student_full_name",
        "student_email",
        "account_status",
        "academic_year",
        "team_code",
        "team_name",
        "team_status",
        "team_role",
        "subject_title",
        "subject_type",
        "defense_status",
        "final_grade",
        "pv_uploaded_at",
        "result_status",
    ]
    JURY_PLANNING_REPORT_COLUMNS = [
        "scheduled_at",
        "location",
        "defense_status",
        "team_code",
        "team_name",
        "subject_title",
        "president",
        "examiners",
        "guests",
        "supervisors",
        "final_grade",
        "pv_uploaded",
    ]

    @staticmethod
    def _user_name(user):
        if user is None:
            return ""
        full_name = getattr(user, "full_name", "") or ""
        return full_name or getattr(user, "matricule", "") or getattr(user, "email", "") or str(user.pk)

    @staticmethod
    def _join_users(users):
        return ", ".join(filter(None, [ReportService._user_name(user) for user in users]))

    @staticmethod
    def _subject_for_team(team):
        return getattr(team, "selected_subject", None)

    @staticmethod
    def _format_datetime(value):
        return value.isoformat() if value else ""

    @staticmethod
    def _format_decimal(value):
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return str(value)
        return str(value)

    @staticmethod
    def _file_url_or_name(file_field):
        if not file_field:
            return ""
        try:
            return file_field.url
        except Exception:
            return getattr(file_field, "name", "") or ""

    @staticmethod
    def _team_participants(team, *, roles=None, statuses=None):
        participants = list(team.participants.all())
        if roles is not None:
            roles = set(roles)
            participants = [participant for participant in participants if participant.role in roles]
        if statuses is not None:
            statuses = set(statuses)
            participants = [participant for participant in participants if participant.status in statuses]
        return sorted(participants, key=lambda item: (item.created_at, item.user_id))

    @staticmethod
    def _student_participants_for_history(team):
        return ReportService._team_participants(
            team,
            roles=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
            statuses=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.ENDED],
        )

    @staticmethod
    def _supervisor_participants_for_history(team):
        return ReportService._team_participants(
            team,
            roles=[TeamParticipant.Role.SUPERVISOR],
            statuses=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.ENDED],
        )

    @staticmethod
    def _leader_for_team(team):
        leaders = ReportService._team_participants(
            team,
            roles=[TeamParticipant.Role.LEADER],
            statuses=[TeamParticipant.Status.ACTIVE],
        )
        if leaders:
            return leaders[0].user
        historical = ReportService._team_participants(
            team,
            roles=[TeamParticipant.Role.LEADER],
            statuses=[TeamParticipant.Status.ENDED],
        )
        return historical[-1].user if historical else None

    @staticmethod
    def _group_jury_users(defense):
        grouped = {
            DefenseJuryAssignment.JuryRole.PRESIDENT: [],
            DefenseJuryAssignment.JuryRole.EXAMINER: [],
            DefenseJuryAssignment.JuryRole.GUEST: [],
        }
        for assignment in defense.jury_assignments.all():
            grouped.setdefault(assignment.role, []).append(assignment.user)
        return grouped

    @staticmethod
    def _base_team_queryset(academic_year):
        return (
            Team.objects.filter(academic_year=academic_year)
            .select_related("academic_year", "selected_subject", "selected_subject__proposed_by")
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=TeamParticipant.objects.select_related("user").order_by("created_at", "user_id"),
                ),
                Prefetch(
                    "defenses",
                    queryset=Defense.objects.select_related("pv_uploaded_by").order_by("-requested_at", "-created_at"),
                ),
            )
        )

    @staticmethod
    def get_defense_report(academic_year):
        defenses = (
            Defense.objects.filter(team__academic_year=academic_year)
            .select_related(
                "team",
                "team__academic_year",
                "team__selected_subject",
                "team__selected_subject__proposed_by",
                "requested_by",
                "scheduled_by",
                "pv_uploaded_by",
            )
            .prefetch_related(
                Prefetch(
                    "team__participants",
                    queryset=TeamParticipant.objects.select_related("user").order_by("created_at", "user_id"),
                ),
                Prefetch(
                    "jury_assignments",
                    queryset=DefenseJuryAssignment.objects.select_related("user").order_by("assigned_at", "user_id"),
                ),
            )
            .order_by("team_id", "scheduled_at", "id")
        )

        rows = []
        for defense in defenses:
            team = defense.team
            subject = ReportService._subject_for_team(team)
            jury = ReportService._group_jury_users(defense)
            supervisors = [participant.user for participant in ReportService._supervisor_participants_for_history(team)]
            rows.append(
                {
                    "defense_id": str(defense.id),
                    "defense_status": defense.status,
                    "team_code": team.pk,
                    "team_name": team.name,
                    "subject_title": getattr(subject, "title", "") or "",
                    "subject_type": getattr(subject, "subject_type", "") or "",
                    "supervisors": ReportService._join_users(supervisors),
                    "jury_president": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.PRESIDENT]),
                    "jury_examiners": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.EXAMINER]),
                    "jury_guests": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.GUEST]),
                    "scheduled_at": ReportService._format_datetime(defense.scheduled_at),
                    "location": defense.location or "",
                    "final_grade": ReportService._format_decimal(defense.final_grade),
                    "deliberation": defense.deliberation or "",
                    "pv_uploaded_at": ReportService._format_datetime(defense.pv_uploaded_at),
                    "pv_uploaded_by": ReportService._user_name(defense.pv_uploaded_by),
                    "pv_file_url_or_name": ReportService._file_url_or_name(defense.pv_file),
                }
            )
        return rows

    @staticmethod
    def get_team_assignment_report(academic_year):
        rows = []
        for team in ReportService._base_team_queryset(academic_year).order_by("team_code"):
            subject = ReportService._subject_for_team(team)
            students = [participant.user for participant in ReportService._student_participants_for_history(team)]
            supervisors = [participant.user for participant in ReportService._supervisor_participants_for_history(team)]
            rows.append(
                {
                    "team_code": team.pk,
                    "team_name": team.name,
                    "team_status": team.status,
                    "selection_round": team.selection_round,
                    "annual_average": ReportService._format_decimal(team.annual_average),
                    "students": ReportService._join_users(students),
                    "leader": ReportService._user_name(ReportService._leader_for_team(team)),
                    "supervisors": ReportService._join_users(supervisors),
                    "subject_title": getattr(subject, "title", "") or "",
                    "subject_type": getattr(subject, "subject_type", "") or "",
                    "subject_status": getattr(subject, "status", "") or "",
                    "subject_proposed_by": ReportService._user_name(getattr(subject, "proposed_by", None)),
                    "assignment_status": "ASSIGNED" if subject else "UNASSIGNED",
                }
            )
        return rows

    @staticmethod
    def _participation_sort_key(participation):
        status_rank = 0 if participation.status == TeamParticipant.Status.ACTIVE else 1
        return (
            status_rank,
            -(participation.joined_at.timestamp() if participation.joined_at else 0),
            -(participation.created_at.timestamp() if participation.created_at else 0),
        )

    @staticmethod
    def _select_student_participation(user):
        participations = list(getattr(user, "report_team_participations", []))
        return sorted(participations, key=ReportService._participation_sort_key)[0] if participations else None

    @staticmethod
    def _selected_defense_for_team(team):
        defenses = list(team.defenses.all())
        completed = [defense for defense in defenses if defense.status == Defense.Status.COMPLETED]
        if completed:
            return sorted(completed, key=lambda item: (item.requested_at, item.created_at), reverse=True)[0]
        return defenses[0] if defenses else None

    @staticmethod
    def _derive_result_status(team, subject, defense):
        if team is None:
            return "NO_TEAM"
        if team.status == Team.Status.DISSOLVED:
            return "ABANDONED"
        if subject is None:
            return "NO_ASSIGNMENT"
        if defense is None:
            return "ASSIGNED_NO_DEFENSE"
        if defense.status == Defense.Status.COMPLETED:
            return "COMPLETED" if defense.final_grade is not None else "DEFENSE_COMPLETED_NO_GRADE"
        if team.status == Team.Status.VALIDATED:
            return "DEFENSE_PENDING"
        return "ASSIGNED_NO_DEFENSE"

    @staticmethod
    def get_student_results_report(academic_year):
        profiles = (
            StudentProfile.objects.filter(academic_year=academic_year)
            .select_related("user", "academic_year")
            .prefetch_related(
                Prefetch(
                    "user__team_participations",
                    queryset=TeamParticipant.objects.select_related(
                        "team",
                        "team__selected_subject",
                        "team__selected_subject__proposed_by",
                    )
                    .prefetch_related(
                        Prefetch(
                            "team__defenses",
                            queryset=Defense.objects.select_related("pv_uploaded_by").order_by(
                                "-requested_at", "-created_at"
                            ),
                        )
                    )
                    .filter(
                        team__academic_year=academic_year,
                        role__in=[TeamParticipant.Role.LEADER, TeamParticipant.Role.MEMBER],
                        status__in=[TeamParticipant.Status.ACTIVE, TeamParticipant.Status.ENDED],
                    ),
                    to_attr="report_team_participations",
                )
            )
            .order_by("user__matricule", "user__last_name", "user__first_name", "user_id")
        )
        rows = []
        for profile in profiles:
            user = profile.user
            participation = ReportService._select_student_participation(user)
            team = participation.team if participation else None
            subject = ReportService._subject_for_team(team) if team else None
            defense = ReportService._selected_defense_for_team(team) if team else None
            rows.append(
                {
                    "student_matricule": user.matricule,
                    "student_full_name": ReportService._user_name(user),
                    "student_email": user.email,
                    "account_status": user.account_status,
                    "academic_year": academic_year.year,
                    "team_code": team.pk if team else "",
                    "team_name": team.name if team else "",
                    "team_status": team.status if team else "",
                    "team_role": participation.role if participation else "",
                    "subject_title": getattr(subject, "title", "") or "",
                    "subject_type": getattr(subject, "subject_type", "") or "",
                    "defense_status": defense.status if defense else "",
                    "final_grade": ReportService._format_decimal(defense.final_grade if defense else None),
                    "pv_uploaded_at": ReportService._format_datetime(defense.pv_uploaded_at if defense else None),
                    "result_status": ReportService._derive_result_status(team, subject, defense),
                }
            )
        return rows

    @staticmethod
    def get_jury_planning_report(academic_year):
        defenses = (
            Defense.objects.filter(team__academic_year=academic_year)
            .select_related("team", "team__selected_subject")
            .prefetch_related(
                Prefetch(
                    "team__participants",
                    queryset=TeamParticipant.objects.select_related("user").order_by("created_at", "user_id"),
                ),
                Prefetch(
                    "jury_assignments",
                    queryset=DefenseJuryAssignment.objects.select_related("user").order_by("assigned_at", "user_id"),
                ),
            )
            .order_by(F("scheduled_at").asc(nulls_last=True), "team_id", "id")
        )
        rows = []
        for defense in defenses:
            team = defense.team
            subject = ReportService._subject_for_team(team)
            jury = ReportService._group_jury_users(defense)
            supervisors = [participant.user for participant in ReportService._supervisor_participants_for_history(team)]
            rows.append(
                {
                    "scheduled_at": ReportService._format_datetime(defense.scheduled_at),
                    "location": defense.location or "",
                    "defense_status": defense.status,
                    "team_code": team.pk,
                    "team_name": team.name,
                    "subject_title": getattr(subject, "title", "") or "",
                    "president": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.PRESIDENT]),
                    "examiners": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.EXAMINER]),
                    "guests": ReportService._join_users(jury[DefenseJuryAssignment.JuryRole.GUEST]),
                    "supervisors": ReportService._join_users(supervisors),
                    "final_grade": ReportService._format_decimal(defense.final_grade),
                    "pv_uploaded": "YES" if defense.pv_uploaded_at else "NO",
                }
            )
        return rows

    @staticmethod
    def _sanitize_csv_cell(value):
        if value is None:
            return ""
        value = str(value)
        if value and value[0] in {"=", "+", "-", "@"}:
            return f"'{value}"
        return value

    @staticmethod
    def to_csv(rows, columns):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: ReportService._sanitize_csv_cell(row.get(column, "")) for column in columns})
        return buffer.getvalue()

    @staticmethod
    def _filename(prefix, academic_year):
        label = (academic_year.year or str(academic_year.pk)).replace("/", "-").replace(" ", "-")
        return f"{prefix}_{label}.csv"

    @staticmethod
    def build_csv_response(rows, columns, filename):
        response = HttpResponse(
            ReportService.to_csv(rows, columns),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def csv_filename_for(report_key, academic_year):
        prefixes = {
            "defenses": "defenses",
            "team_assignments": "team_assignments",
            "student_results": "student_results",
            "jury_planning": "jury_planning",
        }
        return ReportService._filename(prefixes[report_key], academic_year)
