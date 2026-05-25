from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.audit.serializers import AdminActionLogSerializer
from apps.audit.services import AdminActionLogService
from config.pagination import DefaultPageNumberPagination


class SuperAdminActionLogListView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Admin Action Logs"], responses=AdminActionLogSerializer(many=True))
    def get(self, request):
        queryset = AdminActionLogService.list_logs(request.user, filters=request.query_params)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AdminActionLogSerializer(page, many=True).data)
