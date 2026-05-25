from django.urls import path

from apps.defenses.views import (
    AdminDefenseDetailView,
    AdminDefenseListView,
    AdminRescheduleDefenseView,
    AdminScheduleDefenseView,
    AdminUpdateDefenseFilesView,
    AdminUpdateJuryView,
    AdminUploadPVView,
)

urlpatterns = [
    path("defenses/", AdminDefenseListView.as_view(), name="admin-defense-list"),
    path("defenses/<uuid:defense_id>/", AdminDefenseDetailView.as_view(), name="admin-defense-detail"),
    path("defenses/<uuid:defense_id>/schedule/", AdminScheduleDefenseView.as_view(), name="admin-defense-schedule"),
    path(
        "defenses/<uuid:defense_id>/reschedule/",
        AdminRescheduleDefenseView.as_view(),
        name="admin-defense-reschedule",
    ),
    path("defenses/<uuid:defense_id>/jury/", AdminUpdateJuryView.as_view(), name="admin-defense-jury"),
    path("defenses/<uuid:defense_id>/files/", AdminUpdateDefenseFilesView.as_view(), name="admin-defense-files"),
    path("defenses/<uuid:defense_id>/pv/", AdminUploadPVView.as_view(), name="admin-defense-pv"),
]
