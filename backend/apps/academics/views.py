from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.academics.models import AcademicYear
from apps.academics.serializers import AcademicYearSerializer
from config.pagination import DefaultPageNumberPagination


class AdminAcademicYearListCreateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Academic Years"], responses=AcademicYearSerializer(many=True))
    def get(self, request):
        include_archived = request.query_params.get("include_archived", "false").lower()
        queryset = AcademicYear.objects.all()
        if include_archived != "true":
            queryset = queryset.filter(is_archived=False)
        queryset = queryset.order_by("-created_at")
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AcademicYearSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Academic Years"], request=AcademicYearSerializer, responses=AcademicYearSerializer)
    def post(self, request):
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
        if academic_year.is_archived:
            return Response(
                {"detail": "Archived academic year cannot be updated."},
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
        academic_year = get_object_or_404(AcademicYear, pk=pk)
        academic_year.is_archived = True
        academic_year.is_active = False
        academic_year.save(update_fields=["is_archived", "is_active", "updated_at"])
        serializer = AcademicYearSerializer(academic_year)
        return Response(serializer.data, status=status.HTTP_200_OK)
