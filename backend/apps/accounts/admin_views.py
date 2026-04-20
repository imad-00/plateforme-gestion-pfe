from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin_serializers import (
    AdminUserCreateUpdateSerializer,
    AdminUserListSerializer,
    SuperAdminCreateAdminSerializer,
)
from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsSuperAdmin, get_platform_levels
from config.pagination import DefaultPageNumberPagination


class AdminUserListCreateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Users"], responses=AdminUserListSerializer(many=True))
    def get(self, request):
        queryset = User.objects.all().order_by("id")

        business_identity = request.query_params.get("business_identity")
        if business_identity:
            queryset = queryset.filter(business_identity=business_identity)

        account_status = request.query_params.get("account_status")
        if account_status:
            queryset = queryset.filter(account_status=account_status)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminUserListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Admin Users"], request=AdminUserCreateUpdateSerializer, responses=AdminUserListSerializer)
    def post(self, request):
        serializer = AdminUserCreateUpdateSerializer(data=request.data, context={"actor": request.user})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserListSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailUpdateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Users"], responses=AdminUserListSerializer)
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response(AdminUserListSerializer(user).data)

    @extend_schema(tags=["Admin Users"], request=AdminUserCreateUpdateSerializer, responses=AdminUserListSerializer)
    def patch(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        serializer = AdminUserCreateUpdateSerializer(
            target_user,
            data=request.data,
            partial=True,
            context={"actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserListSerializer(user).data)


class AdminUserArchiveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Users"], responses={200: AdminUserListSerializer})
    def post(self, request, pk):
        actor = request.user
        user = get_object_or_404(User, pk=pk)
        actor_levels = get_platform_levels(actor)

        if (
            "ADMIN" in actor_levels
            and "SUPER_ADMIN" not in actor_levels
            and user.business_identity not in {
                User.BusinessIdentity.STUDENT,
                User.BusinessIdentity.TEACHER,
            }
        ):
            return Response(
                {"detail": "ADMIN can only archive STUDENT or TEACHER identities."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.account_status = User.AccountStatus.ARCHIVED
        user.save(update_fields=["account_status", "is_active", "is_archived", "updated_at"])
        return Response(AdminUserListSerializer(user).data, status=status.HTTP_200_OK)


class SuperAdminAdminListCreateView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin"], responses=AdminUserListSerializer(many=True))
    def get(self, request):
        queryset = User.objects.filter(
            platform_access_grants__revoked_at__isnull=True,
            platform_access_grants__access_level__in=["ADMIN", "SUPER_ADMIN"],
        ).distinct().order_by("id")
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminUserListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Super Admin"], request=SuperAdminCreateAdminSerializer, responses=AdminUserListSerializer)
    def post(self, request):
        serializer = SuperAdminCreateAdminSerializer(data=request.data, context={"actor": request.user})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserListSerializer(user).data, status=status.HTTP_201_CREATED)
