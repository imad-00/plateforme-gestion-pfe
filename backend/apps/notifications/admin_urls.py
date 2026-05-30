from django.urls import path

from apps.notifications.views import AdminTestEmailView

urlpatterns = [
    path(
        "notifications/test-email/",
        AdminTestEmailView.as_view(),
        name="admin-notification-test-email",
    ),
]
