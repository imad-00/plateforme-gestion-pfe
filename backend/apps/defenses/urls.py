from django.urls import path

from apps.defenses.views import (
    DefenseAcceptView,
    DefenseDenyView,
    DefenseFilesView,
    DefenseRequestView,
    JuryDefenseDetailView,
    JuryDefenseFilesView,
    JuryDefenseListView,
    JuryUploadPVView,
    MyDefenseView,
    SupervisorDefenseRequestListView,
)

urlpatterns = [
    path("defenses/request/", DefenseRequestView.as_view(), name="defense-request"),
    path("defenses/me/", MyDefenseView.as_view(), name="defense-me"),
    path("defenses/<uuid:defense_id>/files/", DefenseFilesView.as_view(), name="defense-files"),
    path("defenses/<uuid:defense_id>/accept/", DefenseAcceptView.as_view(), name="defense-accept"),
    path("defenses/<uuid:defense_id>/deny/", DefenseDenyView.as_view(), name="defense-deny"),
    path("supervision/defense-requests/", SupervisorDefenseRequestListView.as_view(), name="supervision-defense-requests"),
    path("jury/defenses/", JuryDefenseListView.as_view(), name="jury-defense-list"),
    path("jury/defenses/<uuid:defense_id>/", JuryDefenseDetailView.as_view(), name="jury-defense-detail"),
    path("jury/defenses/<uuid:defense_id>/files/", JuryDefenseFilesView.as_view(), name="jury-defense-files"),
    path("jury/defenses/<uuid:defense_id>/pv/", JuryUploadPVView.as_view(), name="jury-defense-pv"),
]
