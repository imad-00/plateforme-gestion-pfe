from django.urls import path

from apps.deliverables.views import AdminTeamFileListView

urlpatterns = [
    path(
        "teams/<str:team_code>/files/",
        AdminTeamFileListView.as_view(),
        name="admin-team-files",
    ),
]
