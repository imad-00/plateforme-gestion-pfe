from django.urls import path

from apps.assignments.views import (
    AppealSubmitView,
    MyAppealView,
    MyAssignmentResultView,
    MyWishListsView,
    WishListSubmitView,
)

urlpatterns = [
    path("wishlists/", WishListSubmitView.as_view(), name="wishlist-submit"),
    path("wishlists/me/", MyWishListsView.as_view(), name="wishlist-me"),
    path("appeals/", AppealSubmitView.as_view(), name="appeal-submit"),
    path("appeals/me/", MyAppealView.as_view(), name="appeal-me"),
    path("assignments/me/", MyAssignmentResultView.as_view(), name="assignment-result-me"),
]
