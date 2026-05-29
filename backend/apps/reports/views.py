from drf_spectacular.utils import extend_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.academics.models import AcademicYear
from apps.reports.serializers import (
    DefenseReportRowSerializer,
    JuryPlanningReportRowSerializer,
    StudentResultReportRowSerializer,
    TeamAssignmentReportRowSerializer,
)
from apps.reports.services import ReportService


class BaseAcademicYearReportView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    report_key = None
    columns = []
    row_serializer_class = None

    def get_academic_year(self, academic_year_id):
        return get_object_or_404(AcademicYear, pk=academic_year_id)

    def get_rows(self, academic_year):
        raise NotImplementedError

    def response_payload(self, academic_year, rows):
        return {
            "academic_year": {
                "id": academic_year.id,
                "year": academic_year.year,
                "status": academic_year.status,
            },
            "count": len(rows),
            "results": rows,
        }

    def get_json_response(self, academic_year_id):
        academic_year = self.get_academic_year(academic_year_id)
        rows = self.get_rows(academic_year)
        serializer = self.row_serializer_class(rows, many=True)
        return Response(self.response_payload(academic_year, serializer.data))

    def get_csv_response(self, academic_year_id):
        academic_year = self.get_academic_year(academic_year_id)
        rows = self.get_rows(academic_year)
        filename = ReportService.csv_filename_for(self.report_key, academic_year)
        return ReportService.build_csv_response(rows, self.columns, filename)


class DefenseReportView(BaseAcademicYearReportView):
    report_key = "defenses"
    columns = ReportService.DEFENSE_REPORT_COLUMNS
    row_serializer_class = DefenseReportRowSerializer

    def get_rows(self, academic_year):
        return ReportService.get_defense_report(academic_year)

    @extend_schema(tags=["Admin Reports"], responses=DefenseReportRowSerializer(many=True))
    def get(self, request, academic_year_id):
        return self.get_json_response(academic_year_id)


class DefenseReportCSVView(DefenseReportView):
    @extend_schema(tags=["Admin Reports"])
    def get(self, request, academic_year_id):
        return self.get_csv_response(academic_year_id)


class TeamAssignmentReportView(BaseAcademicYearReportView):
    report_key = "team_assignments"
    columns = ReportService.TEAM_ASSIGNMENT_REPORT_COLUMNS
    row_serializer_class = TeamAssignmentReportRowSerializer

    def get_rows(self, academic_year):
        return ReportService.get_team_assignment_report(academic_year)

    @extend_schema(tags=["Admin Reports"], responses=TeamAssignmentReportRowSerializer(many=True))
    def get(self, request, academic_year_id):
        return self.get_json_response(academic_year_id)


class TeamAssignmentReportCSVView(TeamAssignmentReportView):
    @extend_schema(tags=["Admin Reports"])
    def get(self, request, academic_year_id):
        return self.get_csv_response(academic_year_id)


class StudentResultsReportView(BaseAcademicYearReportView):
    report_key = "student_results"
    columns = ReportService.STUDENT_RESULTS_REPORT_COLUMNS
    row_serializer_class = StudentResultReportRowSerializer

    def get_rows(self, academic_year):
        return ReportService.get_student_results_report(academic_year)

    @extend_schema(tags=["Admin Reports"], responses=StudentResultReportRowSerializer(many=True))
    def get(self, request, academic_year_id):
        return self.get_json_response(academic_year_id)


class StudentResultsReportCSVView(StudentResultsReportView):
    @extend_schema(tags=["Admin Reports"])
    def get(self, request, academic_year_id):
        return self.get_csv_response(academic_year_id)


class JuryPlanningReportView(BaseAcademicYearReportView):
    report_key = "jury_planning"
    columns = ReportService.JURY_PLANNING_REPORT_COLUMNS
    row_serializer_class = JuryPlanningReportRowSerializer

    def get_rows(self, academic_year):
        return ReportService.get_jury_planning_report(academic_year)

    @extend_schema(tags=["Admin Reports"], responses=JuryPlanningReportRowSerializer(many=True))
    def get(self, request, academic_year_id):
        return self.get_json_response(academic_year_id)


class JuryPlanningReportCSVView(JuryPlanningReportView):
    @extend_schema(tags=["Admin Reports"])
    def get(self, request, academic_year_id):
        return self.get_csv_response(academic_year_id)
