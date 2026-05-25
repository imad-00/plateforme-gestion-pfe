from django.urls import path

from apps.deliverables.views import (
    DeliverableFileCommentCreateView,
    DeliverableFileDetailView,
    DeliverableFileReviewView,
    DeliverableFileUploadView,
    MyDeliverableFileListView,
    SupervisedTeamFileListView,
    SupervisedTeamListView,
)

urlpatterns = [
    path("deliverable-files/me/", MyDeliverableFileListView.as_view(), name="deliverable-file-me-list"),
    path("deliverable-files/upload/", DeliverableFileUploadView.as_view(), name="deliverable-file-upload"),
    path("deliverable-files/<uuid:file_id>/", DeliverableFileDetailView.as_view(), name="deliverable-file-detail"),
    path(
        "deliverable-files/<uuid:file_id>/comments/",
        DeliverableFileCommentCreateView.as_view(),
        name="deliverable-file-comment-create",
    ),
    path("deliverable-files/<uuid:file_id>/review/", DeliverableFileReviewView.as_view(), name="deliverable-file-review"),
    path("supervision/teams/", SupervisedTeamListView.as_view(), name="supervision-team-list"),
    path("supervision/teams/<str:team_code>/files/", SupervisedTeamFileListView.as_view(), name="supervision-team-files"),
]
