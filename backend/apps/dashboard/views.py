from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.dashboard.services import DashboardService


def _academic_year_param(request):
    return request.query_params.get("academic_year_id")


class AdminDashboardView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Dashboards"], responses=dict)
    def get(self, request):
        return Response(
            DashboardService.get_admin_dashboard(
                request.user,
                academic_year=_academic_year_param(request),
            )
        )


class TeacherDashboardView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Dashboards"], responses=dict)
    def get(self, request):
        return Response(
            DashboardService.get_teacher_dashboard(
                request.user,
                academic_year=_academic_year_param(request),
            )
        )


class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Dashboards"], responses=dict)
    def get(self, request):
        return Response(
            DashboardService.get_student_dashboard(
                request.user,
                academic_year=_academic_year_param(request),
            )
        )
