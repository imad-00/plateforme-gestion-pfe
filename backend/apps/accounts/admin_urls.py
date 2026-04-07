from django.urls import path

from apps.accounts.admin_views import (
    AdminUserArchiveView,
    AdminUserDetailUpdateView,
    AdminUserListCreateView,
)

urlpatterns = [
    path("users/", AdminUserListCreateView.as_view(), name="admin-user-list-create"),
    path("users/<int:pk>/", AdminUserDetailUpdateView.as_view(), name="admin-user-detail-update"),
    path("users/<int:pk>/archive/", AdminUserArchiveView.as_view(), name="admin-user-archive"),
]
