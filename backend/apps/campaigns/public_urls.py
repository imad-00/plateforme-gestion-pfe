from django.urls import path

from apps.campaigns.views import CurrentCampaignView

urlpatterns = [
    path("campaign/current/", CurrentCampaignView.as_view(), name="campaign-current"),
]
