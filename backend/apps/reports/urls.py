from django.urls import path

from apps.reports.views import (
    DefenseReportCSVView,
    DefenseReportView,
    JuryPlanningReportCSVView,
    JuryPlanningReportView,
    StudentResultsReportCSVView,
    StudentResultsReportView,
    TeamAssignmentReportCSVView,
    TeamAssignmentReportView,
)

urlpatterns = [
    path(
        "reports/academic-years/<int:academic_year_id>/defenses/",
        DefenseReportView.as_view(),
        name="admin-report-defenses",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/defenses.csv",
        DefenseReportCSVView.as_view(),
        name="admin-report-defenses-csv",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/team-assignments/",
        TeamAssignmentReportView.as_view(),
        name="admin-report-team-assignments",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/team-assignments.csv",
        TeamAssignmentReportCSVView.as_view(),
        name="admin-report-team-assignments-csv",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/student-results/",
        StudentResultsReportView.as_view(),
        name="admin-report-student-results",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/student-results.csv",
        StudentResultsReportCSVView.as_view(),
        name="admin-report-student-results-csv",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/jury-planning/",
        JuryPlanningReportView.as_view(),
        name="admin-report-jury-planning",
    ),
    path(
        "reports/academic-years/<int:academic_year_id>/jury-planning.csv",
        JuryPlanningReportCSVView.as_view(),
        name="admin-report-jury-planning-csv",
    ),
]
