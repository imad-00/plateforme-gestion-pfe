import csv
import io
from decimal import Decimal

import pytest
from django.utils import timezone
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.academics.models import AcademicYear
from apps.defenses.models import Defense, DefenseJuryAssignment
from apps.deliverables.models import DeliverableFile
from apps.reports.services import ReportService
from apps.teams.models import Team, TeamParticipant
from apps.topics.models import Subject


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def set_student_year(student, academic_year):
    student.student_profile.academic_year = academic_year
    student.student_profile.save(update_fields=["academic_year", "updated_at"])


def create_year(label="2025/2026", status=AcademicYear.Status.ACTIVE):
    return AcademicYear.objects.create(year=label, status=status)


def create_student(user_factory, matricule, email, academic_year, first_name="Student", last_name="Report"):
    student = user_factory(
        matricule=matricule,
        email=email,
        business_identity=User.BusinessIdentity.STUDENT,
        first_name=first_name,
        last_name=last_name,
    )
    set_student_year(student, academic_year)
    return student


def create_teacher(user_factory, matricule, email, first_name="Teacher", last_name="Report"):
    return user_factory(
        matricule=matricule,
        email=email,
        business_identity=User.BusinessIdentity.TEACHER,
        first_name=first_name,
        last_name=last_name,
    )


def create_team(academic_year, code, name, status=Team.Status.VALIDATED, selection_round=Team.SelectionRound.FIRST):
    return Team.objects.create(
        team_code=code,
        academic_year=academic_year,
        name=name,
        status=status,
        selection_round=selection_round,
        annual_average=Decimal("14.50"),
    )


def add_participant(team, user, role, status=TeamParticipant.Status.ACTIVE):
    return TeamParticipant.objects.create(
        team=team,
        user=user,
        role=role,
        status=status,
        joined_at=timezone.now() if status == TeamParticipant.Status.ACTIVE else None,
        ended_at=timezone.now() if status == TeamParticipant.Status.ENDED else None,
    )


def assign_subject(team, teacher, academic_year, code="RPT-SUBJECT"):
    return Subject.objects.create(
        subject_code=code,
        title=f"Subject {code}",
        description="Reporting subject",
        subject_type=Subject.SubjectType.APPLIED_PROJECT,
        status=Subject.Status.ASSIGNED,
        proposed_by=teacher,
        academic_year=academic_year,
        assigned_to_team=team,
    )


def create_deliverable(team, uploader, name="report-work.pdf"):
    return DeliverableFile.objects.create(
        team=team,
        file=f"deliverables/{team.academic_year_id}/{team.pk}/{name}",
        original_filename=name,
        file_size=10,
        content_type="application/pdf",
        uploaded_by=uploader,
    )


def create_defense(team, requester, status=Defense.Status.COMPLETED, **kwargs):
    defaults = {
        "team": team,
        "status": status,
        "requested_by": requester,
        "requested_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Defense.objects.create(**defaults)


def add_jury(defense, admin_user, president, examiners, guests=None):
    DefenseJuryAssignment.objects.create(
        defense=defense,
        user=president,
        role=DefenseJuryAssignment.JuryRole.PRESIDENT,
        assigned_by=admin_user,
    )
    for examiner in examiners:
        DefenseJuryAssignment.objects.create(
            defense=defense,
            user=examiner,
            role=DefenseJuryAssignment.JuryRole.EXAMINER,
            assigned_by=admin_user,
        )
    for guest in guests or []:
        DefenseJuryAssignment.objects.create(
            defense=defense,
            user=guest,
            role=DefenseJuryAssignment.JuryRole.GUEST,
            assigned_by=admin_user,
        )


@pytest.fixture
def report_dataset(db, user_factory, admin_user):
    year = create_year()
    student = create_student(user_factory, "RPT-STU-001", "rpt-stu-1@example.com", year, "Alice", "Student")
    teammate = create_student(user_factory, "RPT-STU-002", "rpt-stu-2@example.com", year, "Bob", "Member")
    no_team_student = create_student(user_factory, "RPT-STU-003", "rpt-stu-3@example.com", year, "No", "Team")
    dissolved_student = create_student(user_factory, "RPT-STU-004", "rpt-stu-4@example.com", year, "Lost", "Student")
    teacher = create_teacher(user_factory, "RPT-TEA-001", "rpt-teacher@example.com", "Tina", "Teacher")
    president = create_teacher(user_factory, "RPT-PRES-001", "rpt-president@example.com", "Paula", "President")
    examiner = create_teacher(user_factory, "RPT-EXAM-001", "rpt-examiner@example.com", "Evan", "Examiner")
    guest = create_teacher(user_factory, "RPT-GUEST-001", "rpt-guest@example.com", "Grace", "Guest")

    assigned_team = create_team(year, "RPT-TEAM-A", "Alpha Team")
    add_participant(assigned_team, student, TeamParticipant.Role.LEADER)
    add_participant(assigned_team, teammate, TeamParticipant.Role.MEMBER)
    add_participant(assigned_team, teacher, TeamParticipant.Role.SUPERVISOR)
    subject = assign_subject(assigned_team, teacher, year, code="RPT-SUB-A")
    defense = create_defense(
        assigned_team,
        student,
        status=Defense.Status.COMPLETED,
        scheduled_at=timezone.now(),
        location="Room 1",
        final_grade=Decimal("16.25"),
        deliberation="Accepted with distinction",
        pv_file="pv/alpha.pdf",
        pv_uploaded_by=president,
        pv_uploaded_at=timezone.now(),
    )
    add_jury(defense, admin_user, president, [examiner], guests=[guest, teacher])

    unassigned_team = create_team(year, "RPT-TEAM-B", "Beta Team", status=Team.Status.LOCKED)
    unassigned_student = create_student(user_factory, "RPT-STU-005", "rpt-stu-5@example.com", year, "Beta", "Student")
    add_participant(unassigned_team, unassigned_student, TeamParticipant.Role.LEADER)

    dissolved_team = create_team(year, "RPT-TEAM-C", "Gamma Team", status=Team.Status.DISSOLVED)
    add_participant(dissolved_team, dissolved_student, TeamParticipant.Role.LEADER, status=TeamParticipant.Status.ENDED)

    unscheduled_defense = create_defense(
        unassigned_team,
        unassigned_student,
        status=Defense.Status.REQUESTED,
    )

    create_deliverable(assigned_team, student)

    return {
        "year": year,
        "student": student,
        "teacher": teacher,
        "president": president,
        "examiner": examiner,
        "guest": guest,
        "assigned_team": assigned_team,
        "unassigned_team": unassigned_team,
        "dissolved_team": dissolved_team,
        "subject": subject,
        "defense": defense,
        "unscheduled_defense": unscheduled_defense,
        "no_team_student": no_team_student,
    }


def csv_rows(response):
    payload = response.content.decode("utf-8")
    return list(csv.DictReader(io.StringIO(payload)))


def report_url(year, report):
    return f"/api/admin/reports/academic-years/{year.id}/{report}/"


def report_csv_url(year, report):
    return f"/api/admin/reports/academic-years/{year.id}/{report}.csv"


@pytest.mark.django_db
def test_non_authenticated_user_cannot_access_reports(report_dataset):
    response = APIClient().get(report_url(report_dataset["year"], "defenses"))

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_student_cannot_access_reports(report_dataset):
    response = auth_client(report_dataset["student"]).get(report_url(report_dataset["year"], "defenses"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_without_admin_grant_cannot_access_reports(report_dataset):
    response = auth_client(report_dataset["teacher"]).get(report_url(report_dataset["year"], "defenses"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_platform_admin_and_super_admin_can_access_reports(report_dataset, admin_user, super_admin_user):
    admin_response = auth_client(admin_user).get(report_url(report_dataset["year"], "defenses"))
    super_admin_response = auth_client(super_admin_user).get(report_url(report_dataset["year"], "defenses"))

    assert admin_response.status_code == 200
    assert super_admin_response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("year_status", [AcademicYear.Status.ACTIVE, AcademicYear.Status.CLOSED, AcademicYear.Status.ARCHIVED])
def test_admin_can_report_on_any_academic_year_status(admin_user, year_status):
    year = create_year(label=f"RPT-{year_status}", status=year_status)

    response = auth_client(admin_user).get(report_url(year, "team-assignments"))

    assert response.status_code == 200
    assert response.json()["academic_year"]["status"] == year_status


@pytest.mark.django_db
def test_defense_report_json_includes_team_subject_supervisors_jury_grade_and_pv(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_url(report_dataset["year"], "defenses"))

    assert response.status_code == 200
    rows = response.json()["results"]
    completed = next(row for row in rows if row["team_code"] == "RPT-TEAM-A")
    assert completed["subject_title"] == "Subject RPT-SUB-A"
    assert "Tina Teacher" in completed["supervisors"]
    assert completed["jury_president"] == "Paula President"
    assert "Evan Examiner" in completed["jury_examiners"]
    assert completed["final_grade"] == "16.25"
    assert completed["pv_uploaded_by"] == "Paula President"
    assert completed["pv_file_url_or_name"]


@pytest.mark.django_db
def test_defense_report_csv_has_expected_headers_rows_and_missing_pv_safe(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_csv_url(report_dataset["year"], "defenses"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    rows = csv_rows(response)
    assert set(["defense_id", "defense_status", "team_code", "pv_uploaded_at"]).issubset(rows[0].keys())
    requested = next(row for row in rows if row["defense_status"] == Defense.Status.REQUESTED)
    assert requested["pv_uploaded_at"] == ""
    assert requested["final_grade"] == ""


@pytest.mark.django_db
def test_team_assignment_report_includes_assigned_unassigned_people_average_and_ordering(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_url(report_dataset["year"], "team-assignments"))

    assert response.status_code == 200
    rows = response.json()["results"]
    assert [row["team_code"] for row in rows] == ["RPT-TEAM-A", "RPT-TEAM-B", "RPT-TEAM-C"]
    assigned = rows[0]
    unassigned = rows[1]
    assert assigned["assignment_status"] == "ASSIGNED"
    assert assigned["leader"] == "Alice Student"
    assert "Bob Member" in assigned["students"]
    assert "Tina Teacher" in assigned["supervisors"]
    assert assigned["annual_average"] == "14.50"
    assert unassigned["assignment_status"] == "UNASSIGNED"
    assert unassigned["subject_title"] == ""


@pytest.mark.django_db
def test_team_assignment_csv_has_expected_headers_and_deterministic_ordering(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_csv_url(report_dataset["year"], "team-assignments"))

    rows = csv_rows(response)
    assert response.status_code == 200
    assert list(rows[0].keys())[0:4] == ["team_code", "team_name", "team_status", "selection_round"]
    assert [row["team_code"] for row in rows] == ["RPT-TEAM-A", "RPT-TEAM-B", "RPT-TEAM-C"]


@pytest.mark.django_db
def test_student_results_report_covers_completed_no_team_abandoned_and_derived_statuses(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_url(report_dataset["year"], "student-results"))

    assert response.status_code == 200
    rows_by_matricule = {row["student_matricule"]: row for row in response.json()["results"]}
    assert rows_by_matricule["RPT-STU-001"]["result_status"] == "COMPLETED"
    assert rows_by_matricule["RPT-STU-001"]["final_grade"] == "16.25"
    assert rows_by_matricule["RPT-STU-003"]["result_status"] == "NO_TEAM"
    assert rows_by_matricule["RPT-STU-004"]["result_status"] == "ABANDONED"
    assert rows_by_matricule["RPT-STU-005"]["result_status"] == "NO_ASSIGNMENT"


@pytest.mark.django_db
def test_student_results_csv_has_expected_headers(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_csv_url(report_dataset["year"], "student-results"))

    rows = csv_rows(response)
    assert response.status_code == 200
    assert "student_matricule" in rows[0]
    assert "result_status" in rows[0]


@pytest.mark.django_db
def test_student_results_report_uses_bounded_queries_for_many_students(user_factory):
    year = create_year(label="2025/2026-N1")
    teacher = create_teacher(user_factory, "RPT-N1-TEA", "rpt-n1-teacher@example.com")
    baseline_students = [
        create_student(user_factory, f"RPT-N1-A-{index}", f"rpt-n1-a-{index}@example.com", year)
        for index in range(2)
    ]
    extra_students = [
        create_student(user_factory, f"RPT-N1-B-{index}", f"rpt-n1-b-{index}@example.com", year)
        for index in range(8)
    ]

    for index, student in enumerate(baseline_students + extra_students):
        team = create_team(year, f"RPT-N1-TEAM-{index:02d}", f"N1 Team {index}")
        add_participant(team, student, TeamParticipant.Role.LEADER)
        assign_subject(team, teacher, year, code=f"RPT-N1-SUB-{index:02d}")
        create_defense(
            team,
            student,
            status=Defense.Status.COMPLETED,
            final_grade=Decimal("12.00"),
            pv_uploaded_at=timezone.now(),
        )

    with CaptureQueriesContext(connection) as baseline_context:
        ReportService.get_student_results_report(year)
    baseline_count = len(baseline_context)

    more_students = [
        create_student(user_factory, f"RPT-N1-C-{index}", f"rpt-n1-c-{index}@example.com", year)
        for index in range(8)
    ]
    offset = len(baseline_students) + len(extra_students)
    for index, student in enumerate(more_students, start=offset):
        team = create_team(year, f"RPT-N1-TEAM-{index:02d}", f"N1 Team {index}")
        add_participant(team, student, TeamParticipant.Role.LEADER)
        assign_subject(team, teacher, year, code=f"RPT-N1-SUB-{index:02d}")
        create_defense(
            team,
            student,
            status=Defense.Status.COMPLETED,
            final_grade=Decimal("13.00"),
            pv_uploaded_at=timezone.now(),
        )

    with CaptureQueriesContext(connection) as expanded_context:
        ReportService.get_student_results_report(year)

    assert len(expanded_context) <= baseline_count + 1


@pytest.mark.django_db
def test_csv_injection_protection_sanitizes_dangerous_cells(user_factory, admin_user):
    year = create_year(label="2025/2026-CSV")
    student = create_student(user_factory, "RPT-CSV-STU", "rpt-csv-student@example.com", year, "Normal", "Student")
    teacher = create_teacher(user_factory, "RPT-CSV-TEA", "rpt-csv-teacher@example.com", "@Advisor", "Teacher")
    team = create_team(year, "RPT-CSV-TEAM", '=HYPERLINK("bad")')
    add_participant(team, student, TeamParticipant.Role.LEADER)
    add_participant(team, teacher, TeamParticipant.Role.SUPERVISOR)
    subject = assign_subject(team, teacher, year, code="RPT-CSV-SUB")
    subject.title = "+Danger"
    subject.subject_type = Subject.SubjectType.APPLIED_PROJECT
    subject.save(update_fields=["title", "subject_type", "updated_at"])
    team.annual_average = Decimal("-12.00")
    team.save(update_fields=["annual_average", "updated_at"])

    response = auth_client(admin_user).get(report_csv_url(year, "team-assignments"))

    assert response.status_code == 200
    row = csv_rows(response)[0]
    assert row["team_name"] == '\'=HYPERLINK("bad")'
    assert row["subject_title"] == "'+Danger"
    assert row["annual_average"] == "'-12.00"
    assert row["supervisors"] == "'@Advisor Teacher"
    assert row["team_code"] == "RPT-CSV-TEAM"


@pytest.mark.django_db
def test_jury_planning_report_includes_scheduled_and_unscheduled_defenses(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_url(report_dataset["year"], "jury-planning"))

    assert response.status_code == 200
    rows = response.json()["results"]
    scheduled = next(row for row in rows if row["team_code"] == "RPT-TEAM-A")
    unscheduled = next(row for row in rows if row["team_code"] == "RPT-TEAM-B")
    assert scheduled["president"] == "Paula President"
    assert "Evan Examiner" in scheduled["examiners"]
    assert scheduled["pv_uploaded"] == "YES"
    assert unscheduled["scheduled_at"] == ""
    assert unscheduled["pv_uploaded"] == "NO"


@pytest.mark.django_db
def test_jury_planning_csv_has_expected_headers(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_csv_url(report_dataset["year"], "jury-planning"))

    rows = csv_rows(response)
    assert response.status_code == 200
    assert list(rows[0].keys())[0:4] == ["scheduled_at", "location", "defense_status", "team_code"]


@pytest.mark.django_db
def test_archived_year_data_hidden_from_normal_teacher_but_available_in_admin_reports(
    user_factory,
    admin_user,
):
    archived_year = create_year(label="2024/2025", status=AcademicYear.Status.ACTIVE)
    teacher = create_teacher(user_factory, "RPT-ARCH-TEA", "rpt-arch-teacher@example.com", "Archive", "Teacher")
    student = create_student(user_factory, "RPT-ARCH-STU", "rpt-arch-student@example.com", archived_year)
    team = create_team(archived_year, "RPT-ARCH-TEAM", "Archived Team")
    add_participant(team, student, TeamParticipant.Role.LEADER)
    add_participant(team, teacher, TeamParticipant.Role.SUPERVISOR)
    assign_subject(team, teacher, archived_year, code="RPT-ARCH-SUB")
    AcademicYear.objects.filter(pk=archived_year.pk).update(status=AcademicYear.Status.ARCHIVED)
    archived_year.refresh_from_db()

    teacher_response = auth_client(teacher).get("/api/teacher/subjects/")
    report_response = auth_client(admin_user).get(report_url(archived_year, "team-assignments"))

    assert teacher_response.status_code == 200
    assert "RPT-ARCH-SUB" not in str(teacher_response.json())
    assert report_response.status_code == 200
    assert report_response.json()["results"][0]["team_code"] == "RPT-ARCH-TEAM"


@pytest.mark.django_db
def test_reports_do_not_mutate_domain_data(report_dataset, admin_user):
    team = report_dataset["assigned_team"]
    defense = report_dataset["defense"]
    before = (team.status, defense.status, Defense.objects.count(), Team.objects.count())

    client = auth_client(admin_user)
    client.get(report_url(report_dataset["year"], "defenses"))
    client.get(report_csv_url(report_dataset["year"], "team-assignments"))
    client.get(report_url(report_dataset["year"], "student-results"))
    client.get(report_csv_url(report_dataset["year"], "jury-planning"))

    team.refresh_from_db()
    defense.refresh_from_db()
    after = (team.status, defense.status, Defense.objects.count(), Team.objects.count())
    assert after == before


@pytest.mark.django_db
def test_csv_responses_use_text_csv_and_attachment_filename(report_dataset, admin_user):
    response = auth_client(admin_user).get(report_csv_url(report_dataset["year"], "jury-planning"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert 'filename="jury_planning_2025-2026.csv"' in response["Content-Disposition"]
