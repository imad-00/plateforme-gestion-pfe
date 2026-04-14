from django.urls import path

from apps.topics.views import PublicSubjectDetailView, PublicSubjectListView

urlpatterns = [
    path("subjects/", PublicSubjectListView.as_view(), name="public-subject-list"),
    path("subjects/<int:pk>/", PublicSubjectDetailView.as_view(), name="public-subject-detail"),
]
