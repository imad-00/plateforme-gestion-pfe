from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    IsAdminOrSuperAdmin,
    IsAuthenticatedAndActiveAccount,
    IsTeacherOrAbove,
)
from apps.academics.models import AcademicYear
from apps.assignments.services import WishListService
from apps.teams.services import TeamService
from apps.topics.models import Subject
from apps.topics.serializers import (
    AdminSubjectListSerializer,
    PublicSubjectSerializer,
    RejectSubjectSerializer,
    SubjectWorkflowService,
    TeacherSubjectListSerializer,
    TeacherSubjectWriteSerializer,
)
from config.pagination import DefaultPageNumberPagination


class TeacherSubjectListCreateView(APIView):
    permission_classes = [IsTeacherOrAbove]

    @extend_schema(tags=["Teacher Subjects"], responses=TeacherSubjectListSerializer(many=True))
    def get(self, request):
        queryset = Subject.objects.filter(proposed_by=request.user).select_related(
            "academic_year", "reviewed_by"
        )
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = TeacherSubjectListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Teacher Subjects"], request=TeacherSubjectWriteSerializer, responses=TeacherSubjectListSerializer)
    def post(self, request):
        serializer = TeacherSubjectWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        subject = serializer.save()
        return Response(TeacherSubjectListSerializer(subject).data, status=status.HTTP_201_CREATED)


class TeacherSubjectDetailUpdateView(APIView):
    permission_classes = [IsTeacherOrAbove]

    def _get_subject(self, request, pk):
        return get_object_or_404(
            Subject.objects.select_related("academic_year", "reviewed_by"),
            pk=pk,
            proposed_by=request.user,
        )

    @extend_schema(tags=["Teacher Subjects"], responses=TeacherSubjectListSerializer)
    def get(self, request, pk):
        subject = self._get_subject(request, pk)
        return Response(TeacherSubjectListSerializer(subject).data)

    @extend_schema(tags=["Teacher Subjects"], request=TeacherSubjectWriteSerializer, responses=TeacherSubjectListSerializer)
    def patch(self, request, pk):
        subject = self._get_subject(request, pk)
        serializer = TeacherSubjectWriteSerializer(
            subject,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(TeacherSubjectListSerializer(updated).data)


class TeacherSubjectSubmitView(APIView):
    permission_classes = [IsTeacherOrAbove]

    @extend_schema(tags=["Teacher Subjects"], responses=TeacherSubjectListSerializer)
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk, proposed_by=request.user)
        subject = SubjectWorkflowService.submit(subject)
        return Response(TeacherSubjectListSerializer(subject).data, status=status.HTTP_200_OK)


class TeacherSubjectResubmitView(APIView):
    permission_classes = [IsTeacherOrAbove]

    @extend_schema(tags=["Teacher Subjects"], responses=TeacherSubjectListSerializer)
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk, proposed_by=request.user)
        subject = SubjectWorkflowService.resubmit(subject)
        return Response(TeacherSubjectListSerializer(subject).data, status=status.HTTP_200_OK)


class AdminSubjectListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Subjects"], responses=AdminSubjectListSerializer(many=True))
    def get(self, request):
        queryset = Subject.objects.select_related("proposed_by", "academic_year", "reviewed_by")

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        academic_year = request.query_params.get("academic_year")
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)

        proposed_by = request.query_params.get("proposed_by")
        if proposed_by:
            queryset = queryset.filter(proposed_by_id=proposed_by)

        archived = request.query_params.get("archived")
        if archived in {"true", "false"}:
            if archived == "true":
                queryset = queryset.filter(status=Subject.Status.ARCHIVED)
            else:
                queryset = queryset.exclude(status=Subject.Status.ARCHIVED)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset.order_by("-created_at"), request)
        serializer = AdminSubjectListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminSubjectDetailView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Subjects"], responses=AdminSubjectListSerializer)
    def get(self, request, pk):
        subject = get_object_or_404(
            Subject.objects.select_related("proposed_by", "academic_year", "reviewed_by"),
            pk=pk,
        )
        return Response(AdminSubjectListSerializer(subject).data)


class AdminSubjectApproveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Subjects"], responses=AdminSubjectListSerializer)
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        subject = SubjectWorkflowService.approve(subject, reviewer=request.user)
        return Response(AdminSubjectListSerializer(subject).data, status=status.HTTP_200_OK)


class AdminSubjectRejectView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Subjects"], request=RejectSubjectSerializer, responses=AdminSubjectListSerializer)
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        serializer = RejectSubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = SubjectWorkflowService.reject(
            subject,
            reviewer=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(AdminSubjectListSerializer(subject).data, status=status.HTTP_200_OK)


class AdminSubjectArchiveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Subjects"], responses=AdminSubjectListSerializer)
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        subject = SubjectWorkflowService.archive(subject)
        return Response(AdminSubjectListSerializer(subject).data, status=status.HTTP_200_OK)


class PublicSubjectListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Subjects Catalog"], responses=PublicSubjectSerializer(many=True))
    def get(self, request):
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        queryset = Subject.objects.none()

        if active_year is not None:
            team = TeamService.get_active_student_team(request.user)
            if team is not None:
                WishListService.ensure_catalog_open_for_team(team)
                queryset = WishListService.get_available_subjects_for_team(team)
            else:
                queryset = WishListService.get_available_subjects_for_user_without_team()

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset.order_by("-created_at"), request)
        serializer = PublicSubjectSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicSubjectDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Subjects Catalog"], responses=PublicSubjectSerializer)
    def get(self, request, pk):
        active_year = AcademicYear.objects.filter(status=AcademicYear.Status.ACTIVE).first()
        if active_year is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        team = TeamService.get_active_student_team(request.user)
        if team is not None:
            WishListService.ensure_catalog_open_for_team(team)
            queryset = WishListService.get_available_subjects_for_team(team)
        else:
            queryset = WishListService.get_available_subjects_for_user_without_team()
        subject = get_object_or_404(queryset, pk=pk)
        return Response(PublicSubjectSerializer(subject).data)
