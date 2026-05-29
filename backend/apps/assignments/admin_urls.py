from django.urls import path

from apps.assignments.views import (
    AdminAppealAcceptView,
    AdminAppealListView,
    AdminAppealRejectView,
    AdminAssignmentValidateView,
    AdminManualAssignmentView,
    AdminMeritAssignmentView,
    AdminRandomAssignmentView,
    AdminWishListDetailView,
    AdminWishListListView,
)

urlpatterns = [
    path("wishlists/", AdminWishListListView.as_view(), name="admin-wishlist-list"),
    path("wishlists/<uuid:wishlist_id>/", AdminWishListDetailView.as_view(), name="admin-wishlist-detail"),
    path("assignments/merit/", AdminMeritAssignmentView.as_view(), name="admin-assignment-merit"),
    path("assignments/random/", AdminRandomAssignmentView.as_view(), name="admin-assignment-random"),
    path("assignments/manual/", AdminManualAssignmentView.as_view(), name="admin-assignment-manual"),
    path(
        "assignments/<str:team_code>/validate/",
        AdminAssignmentValidateView.as_view(),
        name="admin-assignment-validate",
    ),
    path("appeals/", AdminAppealListView.as_view(), name="admin-appeal-list"),
    path("appeals/<uuid:appeal_id>/accept/", AdminAppealAcceptView.as_view(), name="admin-appeal-accept"),
    path("appeals/<uuid:appeal_id>/reject/", AdminAppealRejectView.as_view(), name="admin-appeal-reject"),
]
