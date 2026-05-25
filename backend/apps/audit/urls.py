from django.urls import path

from apps.audit.views import SuperAdminActionLogListView


urlpatterns = [
    path("audit/admin-actions/", SuperAdminActionLogListView.as_view(), name="super-admin-audit-admin-actions"),
]
