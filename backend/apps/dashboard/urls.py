from django.urls import path

from apps.dashboard.views import AdminDashboardView, StudentDashboardView, TeacherDashboardView


urlpatterns = [
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
    path("dashboard/teacher/", TeacherDashboardView.as_view(), name="dashboard-teacher"),
    path("dashboard/student/", StudentDashboardView.as_view(), name="dashboard-student"),
]
