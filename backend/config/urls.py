from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.api import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/admin/", include("apps.academics.urls")),
    path("api/admin/", include("apps.campaigns.urls")),
    path("api/admin/", include("apps.accounts.admin_urls")),
    path("api/admin/", include("apps.topics.admin_urls")),
    path("api/admin/", include("apps.teams.admin_urls")),
    path("api/admin/", include("apps.assignments.admin_urls")),
    path("api/super-admin/", include("apps.accounts.super_admin_urls")),
    path("api/teacher/", include("apps.topics.teacher_urls")),
    path("api/", include("apps.campaigns.public_urls")),
    path("api/", include("apps.teams.urls")),
    path("api/", include("apps.assignments.urls")),
    path("api/", include("apps.deliverables.urls")),
    path("api/", include("apps.topics.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]
