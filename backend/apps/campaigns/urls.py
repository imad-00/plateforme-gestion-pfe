from django.urls import path

from apps.campaigns.views import (
    AdminCampaignPhaseArchiveView,
    AdminCampaignPhaseDetailUpdateView,
    AdminCampaignPhaseListCreateView,
)

urlpatterns = [
    path("campaign-phases/", AdminCampaignPhaseListCreateView.as_view(), name="admin-campaign-phase-list-create"),
    path(
        "campaign-phases/<int:pk>/",
        AdminCampaignPhaseDetailUpdateView.as_view(),
        name="admin-campaign-phase-detail-update",
    ),
    path(
        "campaign-phases/<int:pk>/archive/",
        AdminCampaignPhaseArchiveView.as_view(),
        name="admin-campaign-phase-archive",
    ),
]
