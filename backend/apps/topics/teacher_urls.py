from django.urls import path

from apps.topics.views import (
    TeacherSubjectDetailUpdateView,
    TeacherSubjectListCreateView,
    TeacherSubjectResubmitView,
    TeacherSubjectSubmitView,
)

urlpatterns = [
    path("subjects/", TeacherSubjectListCreateView.as_view(), name="teacher-subject-list-create"),
    path("subjects/<int:pk>/", TeacherSubjectDetailUpdateView.as_view(), name="teacher-subject-detail-update"),
    path("subjects/<int:pk>/submit/", TeacherSubjectSubmitView.as_view(), name="teacher-subject-submit"),
    path("subjects/<int:pk>/resubmit/", TeacherSubjectResubmitView.as_view(), name="teacher-subject-resubmit"),
]
