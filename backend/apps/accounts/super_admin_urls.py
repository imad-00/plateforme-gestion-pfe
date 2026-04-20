from django.urls import path

from apps.accounts.admin_views import SuperAdminAdminListCreateView
from apps.accounts.platform_views import (
    SuperAdminPlatformAccessGrantCreateView,
    SuperAdminPlatformAccessGrantRevokeView,
)

urlpatterns = [
    path("admins/", SuperAdminAdminListCreateView.as_view(), name="super-admin-admins-list-create"),
    path(
        "platform-access-grants/",
        SuperAdminPlatformAccessGrantCreateView.as_view(),
        name="super-admin-platform-access-grant-create",
    ),
    path(
        "platform-access-grants/<int:pk>/revoke/",
        SuperAdminPlatformAccessGrantRevokeView.as_view(),
        name="super-admin-platform-access-grant-revoke",
    ),
]
