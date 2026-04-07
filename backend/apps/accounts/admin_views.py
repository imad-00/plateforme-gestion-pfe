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
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from config.pagination import DefaultPageNumberPagination


class AdminUserListCreateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Users"], responses=AdminUserListSerializer(many=True))
    def get(self, request):
        queryset = User.objects.all().order_by("id")

        role = request.query_params.get("global_role")
        if role:
            queryset = queryset.filter(global_role=role)

        is_archived = request.query_params.get("is_archived")
        if is_archived in {"true", "false"}:
            queryset = queryset.filter(is_archived=(is_archived == "true"))

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

        if actor.global_role == User.GlobalRole.ADMIN and user.global_role not in {
            User.GlobalRole.STUDENT,
            User.GlobalRole.TEACHER,
        }:
            return Response(
                {"detail": "ADMIN can only archive STUDENT or TEACHER accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_archived = True
        user.is_active = False
        user.save(update_fields=["is_archived", "is_active", "updated_at"])
        return Response(AdminUserListSerializer(user).data, status=status.HTTP_200_OK)


class SuperAdminAdminListCreateView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin"], responses=AdminUserListSerializer(many=True))
    def get(self, request):
        queryset = User.objects.filter(
            global_role__in=[User.GlobalRole.ADMIN, User.GlobalRole.SUPER_ADMIN]
        ).order_by("id")
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminUserListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Super Admin"], request=SuperAdminCreateAdminSerializer, responses=AdminUserListSerializer)
    def post(self, request):
        serializer = SuperAdminCreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserListSerializer(user).data, status=status.HTTP_201_CREATED)
