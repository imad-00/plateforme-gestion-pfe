from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import PlatformAccessGrant
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from apps.accounts.platform_serializers import (
    PlatformAccessGrantCreateSerializer,
    PlatformAccessGrantReadSerializer,
    PlatformAccessGrantRevokeSerializer,
)
from apps.audit.models import AdminActionLog
from apps.audit.services import AdminActionLogService
from config.pagination import DefaultPageNumberPagination


class AdminPlatformAccessGrantListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Platform Access"], responses=PlatformAccessGrantReadSerializer(many=True))
    def get(self, request):
        queryset = PlatformAccessGrant.objects.select_related("user", "granted_by").order_by("-granted_at")

        access_level = request.query_params.get("access_level")
        if access_level:
            queryset = queryset.filter(access_level=access_level)

        user_id = request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        is_active = request.query_params.get("is_active")
        if is_active in {"true", "false"}:
            if is_active == "true":
                queryset = queryset.filter(revoked_at__isnull=True)
            else:
                queryset = queryset.filter(revoked_at__isnull=False)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PlatformAccessGrantReadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class SuperAdminPlatformAccessGrantCreateView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        tags=["Platform Access"],
        request=PlatformAccessGrantCreateSerializer,
        responses=PlatformAccessGrantReadSerializer,
    )
    def post(self, request):
        serializer = PlatformAccessGrantCreateSerializer(data=request.data, context={"actor": request.user})
        serializer.is_valid(raise_exception=True)
        grant = serializer.save()
        AdminActionLogService.log(
            request.user,
            AdminActionLog.ActionType.PLATFORM_GRANT_CREATED,
            target=grant,
            metadata={"user_id": grant.user_id, "access_level": grant.access_level},
            request=request,
        )
        return Response(PlatformAccessGrantReadSerializer(grant).data, status=status.HTTP_201_CREATED)


class SuperAdminPlatformAccessGrantRevokeView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        tags=["Platform Access"],
        request=PlatformAccessGrantRevokeSerializer,
        responses=PlatformAccessGrantReadSerializer,
    )
    def post(self, request, pk):
        grant = get_object_or_404(PlatformAccessGrant.objects.select_related("user"), pk=pk)
        serializer = PlatformAccessGrantRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = serializer.revoke(grant)
        AdminActionLogService.log(
            request.user,
            AdminActionLog.ActionType.PLATFORM_GRANT_REVOKED,
            target=grant,
            metadata={"user_id": grant.user_id, "access_level": grant.access_level},
            request=request,
        )
        return Response(PlatformAccessGrantReadSerializer(grant).data, status=status.HTTP_200_OK)
