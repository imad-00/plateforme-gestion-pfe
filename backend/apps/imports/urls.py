from django.urls import path

from apps.imports.views import UserImportConfirmView, UserImportPreviewView, UserImportTemplateView


urlpatterns = [
    path("imports/users/preview/", UserImportPreviewView.as_view(), name="admin-user-import-preview"),
    path("imports/users/confirm/", UserImportConfirmView.as_view(), name="admin-user-import-confirm"),
    path("imports/users/template/", UserImportTemplateView.as_view(), name="admin-user-import-template"),
]
