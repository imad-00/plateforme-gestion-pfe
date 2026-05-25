from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, get_platform_levels
from apps.academics.models import AcademicYear
from apps.academics.serializers import AcademicYearSerializer
from apps.archives.serializers import AcademicYearLifecycleActionSerializer
from apps.archives.services import AcademicYearLifecycleService
from config.pagination import DefaultPageNumberPagination


class AdminAcademicYearListCreateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Academic Years"], responses=AcademicYearSerializer(many=True))
    def get(self, request):
        include_archived = request.query_params.get("include_archived", "false").lower()
        queryset = AcademicYear.objects.all()
        if include_archived != "true":
            queryset = queryset.exclude(status=AcademicYear.Status.ARCHIVED)
        queryset = queryset.order_by("-created_at")
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AcademicYearSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Academic Years"], request=AcademicYearSerializer, responses=AcademicYearSerializer)
    def post(self, request):
        if "SUPER_ADMIN" not in get_platform_levels(request.user):
            return Response(
                {"detail": "SUPER_ADMIN platform access is required to create academic years."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AcademicYearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminAcademicYearDetailUpdateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Academic Years"], responses=AcademicYearSerializer)
    def get(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        serializer = AcademicYearSerializer(academic_year)
        return Response(serializer.data)

    @extend_schema(tags=["Academic Years"], request=AcademicYearSerializer, responses=AcademicYearSerializer)
    def patch(self, request, pk):
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        if academic_year.status != AcademicYear.Status.ACTIVE:
            return Response(
                {"detail": "Only ACTIVE academic years can be updated through the normal admin endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "status" in request.data:
            return Response(
                {"status": "Use the super-admin lifecycle endpoints to close, reopen, or archive academic years."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AcademicYearSerializer(academic_year, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminAcademicYearArchiveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Academic Years"], responses={200: AcademicYearSerializer})
    def post(self, request, pk):
        if "SUPER_ADMIN" not in get_platform_levels(request.user):
            return Response(
                {"detail": "SUPER_ADMIN platform access is required to archive academic years."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
            {"academic_year": AcademicYearSerializer(academic_year).data, "event_id": event.id},
            status=status.HTTP_200_OK,
        )
