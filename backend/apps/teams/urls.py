from django.urls import path

from apps.teams.views import (
    LeaveTeamView,
    MyTeamView,
    ReceivedTeamInvitationsView,
    TeamInvitationAcceptView,
    TeamInvitationRejectView,
    TeamInviteStudentView,
    TeamLockView,
    TeamRemoveMemberView,
    TeamTransferLeadershipView,
)

urlpatterns = [
    path("teams/me/", MyTeamView.as_view(), name="team-me"),
    path("teams/leave/", LeaveTeamView.as_view(), name="team-leave"),
    path("teams/<str:team_code>/invite/", TeamInviteStudentView.as_view(), name="team-invite"),
    path("teams/<str:team_code>/remove-member/", TeamRemoveMemberView.as_view(), name="team-remove-member"),
    path(
        "teams/<str:team_code>/transfer-leadership/",
        TeamTransferLeadershipView.as_view(),
        name="team-transfer-leadership",
    ),
    path("teams/<str:team_code>/lock/", TeamLockView.as_view(), name="team-lock"),
    # must be before the <uuid> patterns so "received" isn't matched as a uuid
    path("team-invitations/received/", ReceivedTeamInvitationsView.as_view(), name="team-invitations-received"),
    path(
        "team-invitations/<uuid:participation_id>/accept/",
        TeamInvitationAcceptView.as_view(),
        name="team-invitation-accept",
    ),
    path(
        "team-invitations/<uuid:participation_id>/reject/",
        TeamInvitationRejectView.as_view(),
        name="team-invitation-reject",
    ),
]
