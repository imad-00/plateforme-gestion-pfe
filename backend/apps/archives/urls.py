from django.urls import path

from apps.archives.views import (
    SuperAdminAcademicYearLifecycleEventListView,
    SuperAdminArchiveAcademicYearView,
    SuperAdminCloseAcademicYearView,
    SuperAdminCloseAndArchiveAcademicYearView,
    SuperAdminClosureReadinessView,
    SuperAdminReopenAcademicYearView,
)

urlpatterns = [
    path(
        "academic-years/<int:pk>/closure-readiness/",
        SuperAdminClosureReadinessView.as_view(),
        name="super-admin-academic-year-closure-readiness",
    ),
    path(
        "academic-years/<int:pk>/close/",
        SuperAdminCloseAcademicYearView.as_view(),
        name="super-admin-academic-year-close",
    ),
    path(
        "academic-years/<int:pk>/reopen/",
        SuperAdminReopenAcademicYearView.as_view(),
        name="super-admin-academic-year-reopen",
    ),
    path(
        "academic-years/<int:pk>/archive/",
        SuperAdminArchiveAcademicYearView.as_view(),
        name="super-admin-academic-year-archive",
    ),
    path(
        "academic-years/<int:pk>/close-and-archive/",
        SuperAdminCloseAndArchiveAcademicYearView.as_view(),
        name="super-admin-academic-year-close-and-archive",
    ),
    path(
        "academic-years/<int:pk>/lifecycle-events/",
        SuperAdminAcademicYearLifecycleEventListView.as_view(),
        name="super-admin-academic-year-lifecycle-events",
    ),
]
