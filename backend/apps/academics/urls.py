from django.urls import path

from apps.academics.views import (
    AdminAcademicYearArchiveView,
    AdminAcademicYearDetailUpdateView,
    AdminAcademicYearListCreateView,
)

urlpatterns = [
    path("academic-years/", AdminAcademicYearListCreateView.as_view(), name="admin-academic-year-list-create"),
    path("academic-years/<int:pk>/", AdminAcademicYearDetailUpdateView.as_view(), name="admin-academic-year-detail-update"),
    path("academic-years/<int:pk>/archive/", AdminAcademicYearArchiveView.as_view(), name="admin-academic-year-archive"),
]
