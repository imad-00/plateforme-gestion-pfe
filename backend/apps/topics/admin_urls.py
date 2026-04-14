from django.urls import path

from apps.topics.views import (
    AdminSubjectApproveView,
    AdminSubjectArchiveView,
    AdminSubjectDetailView,
    AdminSubjectListView,
    AdminSubjectRejectView,
)

urlpatterns = [
    path("subjects/", AdminSubjectListView.as_view(), name="admin-subject-list"),
    path("subjects/<int:pk>/", AdminSubjectDetailView.as_view(), name="admin-subject-detail"),
    path("subjects/<int:pk>/approve/", AdminSubjectApproveView.as_view(), name="admin-subject-approve"),
    path("subjects/<int:pk>/reject/", AdminSubjectRejectView.as_view(), name="admin-subject-reject"),
    path("subjects/<int:pk>/archive/", AdminSubjectArchiveView.as_view(), name="admin-subject-archive"),
]
