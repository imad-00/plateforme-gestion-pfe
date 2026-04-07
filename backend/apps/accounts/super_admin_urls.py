from django.urls import path

from apps.accounts.admin_views import SuperAdminAdminListCreateView

urlpatterns = [
    path("admins/", SuperAdminAdminListCreateView.as_view(), name="super-admin-admins-list-create"),
]
