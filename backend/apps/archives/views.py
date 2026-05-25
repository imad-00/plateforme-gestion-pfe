from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.academics.models import AcademicYear
from apps.academics.serializers import AcademicYearSerializer
from apps.archives.models import AcademicYearLifecycleEvent
from apps.archives.serializers import (
    AcademicYearLifecycleActionSerializer,
    AcademicYearLifecycleEventSerializer,
)
from apps.archives.services import AcademicYearLifecycleService
from config.pagination import DefaultPageNumberPagination


class SuperAdminClosureReadinessView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], responses=dict)
    def get(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        return Response(
            AcademicYearLifecycleService.check_closure_readiness(academic_year),
            status=status.HTTP_200_OK,
        )


class SuperAdminCloseAcademicYearView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], request=AcademicYearLifecycleActionSerializer)
    def post(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        serializer = AcademicYearLifecycleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        academic_year, event, readiness = AcademicYearLifecycleService.close_year(
            request.user,
            academic_year,
            reason=serializer.validated_data["reason"],
            force=serializer.validated_data.get("force", False),
            confirm=serializer.validated_data["confirm"],
        )
        return Response(
            {
                "academic_year": AcademicYearSerializer(academic_year).data,
                "event": AcademicYearLifecycleEventSerializer(event).data,
                "readiness": readiness,
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminReopenAcademicYearView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], request=AcademicYearLifecycleActionSerializer)
    def post(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        serializer = AcademicYearLifecycleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        academic_year, event = AcademicYearLifecycleService.reopen_year(
            request.user,
            academic_year,
            reason=serializer.validated_data["reason"],
            confirm=serializer.validated_data["confirm"],
        )
        return Response(
            {
                "academic_year": AcademicYearSerializer(academic_year).data,
                "event": AcademicYearLifecycleEventSerializer(event).data,
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminArchiveAcademicYearView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], request=AcademicYearLifecycleActionSerializer)
    def post(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        serializer = AcademicYearLifecycleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        academic_year, event = AcademicYearLifecycleService.archive_year(
            request.user,
            academic_year,
            reason=serializer.validated_data["reason"],
            confirm=serializer.validated_data["confirm"],
        )
        return Response(
            {
                "academic_year": AcademicYearSerializer(academic_year).data,
                "event": AcademicYearLifecycleEventSerializer(event).data,
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminCloseAndArchiveAcademicYearView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], request=AcademicYearLifecycleActionSerializer)
    def post(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        serializer = AcademicYearLifecycleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        academic_year, close_event, archive_event, readiness = AcademicYearLifecycleService.close_and_archive_year(
            request.user,
            academic_year,
            reason=serializer.validated_data["reason"],
            force=serializer.validated_data.get("force", False),
            confirm=serializer.validated_data["confirm"],
        )
        return Response(
            {
                "academic_year": AcademicYearSerializer(academic_year).data,
                "close_event": None
                if close_event is None
                else AcademicYearLifecycleEventSerializer(close_event).data,
                "archive_event": AcademicYearLifecycleEventSerializer(archive_event).data,
                "readiness": readiness,
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminAcademicYearLifecycleEventListView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(tags=["Super Admin Academic Year Lifecycle"], responses=AcademicYearLifecycleEventSerializer(many=True))
    def get(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        queryset = AcademicYearLifecycleEvent.objects.filter(academic_year=academic_year).select_related(
            "academic_year",
            "performed_by",
        )
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AcademicYearLifecycleEventSerializer(page, many=True).data)
