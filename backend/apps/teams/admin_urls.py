from django.urls import path

from apps.teams.views import (
    AdminTeamDetailView,
    AdminTeamDissolveView,
    AdminTeamListView,
    AdminTeamRemoveMemberView,
    AdminTeamSupervisorAddView,
    AdminTeamSupervisorRemoveView,
    AdminTeamTransferLeadershipView,
)

urlpatterns = [
    path("teams/", AdminTeamListView.as_view(), name="admin-team-list"),
    path("teams/<str:team_code>/", AdminTeamDetailView.as_view(), name="admin-team-detail"),
    path("teams/<str:team_code>/remove-member/", AdminTeamRemoveMemberView.as_view(), name="admin-team-remove-member"),
    path(
        "teams/<str:team_code>/transfer-leadership/",
        AdminTeamTransferLeadershipView.as_view(),
        name="admin-team-transfer-leadership",
    ),
    path("teams/<str:team_code>/supervisors/", AdminTeamSupervisorAddView.as_view(), name="admin-team-add-supervisor"),
    path(
        "teams/<str:team_code>/supervisors/remove/",
        AdminTeamSupervisorRemoveView.as_view(),
        name="admin-team-remove-supervisor",
    ),
    path("teams/<str:team_code>/dissolve/", AdminTeamDissolveView.as_view(), name="admin-team-dissolve"),
]
