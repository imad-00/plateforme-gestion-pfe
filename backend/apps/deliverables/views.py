from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.deliverables.models import DeliverableFile
from apps.deliverables.serializers import (
    DeliverableFileCommentCreateSerializer,
    DeliverableFileCommentSerializer,
    DeliverableFileReviewSerializer,
    DeliverableFileSerializer,
    DeliverableFileUploadSerializer,
    SupervisedTeamSerializer,
)
from apps.deliverables.services import DeliverableFileService
from apps.teams.models import Team
from config.pagination import DefaultPageNumberPagination


class MyDeliverableFileListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Deliverable Files"], responses=DeliverableFileSerializer(many=True))
    def get(self, request):
        queryset = DeliverableFileService.list_team_files(request.user)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DeliverableFileSerializer(page, many=True).data)


class DeliverableFileUploadView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Deliverable Files"], request=DeliverableFileUploadSerializer, responses=DeliverableFileSerializer)
    def post(self, request):
        serializer = DeliverableFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deliverable_file = DeliverableFileService.upload_file(
            request.user,
            serializer.validated_data["file"],
            serializer.validated_data.get("comment", ""),
        )
        return Response(DeliverableFileSerializer(deliverable_file).data, status=status.HTTP_201_CREATED)


class DeliverableFileDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Deliverable Files"], responses=DeliverableFileSerializer)
    def get(self, request, file_id):
        deliverable_file = get_object_or_404(
            DeliverableFile.objects.select_related("team", "uploaded_by", "reviewed_by"),
            pk=file_id,
        )
        if not DeliverableFileService.can_access_file(request.user, deliverable_file):
            return Response({"detail": "You do not have access to this file."}, status=status.HTTP_403_FORBIDDEN)
        return Response(DeliverableFileSerializer(deliverable_file).data, status=status.HTTP_200_OK)


class DeliverableFileCommentCreateView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Deliverable Files"], request=DeliverableFileCommentCreateSerializer, responses=DeliverableFileCommentSerializer)
    def post(self, request, file_id):
        deliverable_file = get_object_or_404(DeliverableFile, pk=file_id)
        serializer = DeliverableFileCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = DeliverableFileService.add_comment(request.user, deliverable_file, serializer.validated_data["text"])
        return Response(DeliverableFileCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class SupervisedTeamListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], responses=SupervisedTeamSerializer(many=True))
    def get(self, request):
        queryset = DeliverableFileService.list_supervised_teams(request.user)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset.order_by("team_code"), request)
        return paginator.get_paginated_response(SupervisedTeamSerializer(page, many=True).data)


class SupervisedTeamFileListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], responses=DeliverableFileSerializer(many=True))
    def get(self, request, team_code):
        team = get_object_or_404(Team.objects.select_related("academic_year"), pk=team_code)
        queryset = DeliverableFileService.list_files_for_supervised_team(request.user, team)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DeliverableFileSerializer(page, many=True).data)


class AdminTeamFileListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Deliverables"], responses=DeliverableFileSerializer(many=True))
    def get(self, request, team_code):
        team = get_object_or_404(Team.objects.select_related("academic_year"), pk=team_code)
        queryset = (
            DeliverableFile.objects.filter(team=team)
            .select_related("team", "uploaded_by", "reviewed_by")
            .prefetch_related("comments__author")
            .order_by("-uploaded_at")
        )
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DeliverableFileSerializer(page, many=True).data)


class DeliverableFileReviewView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], request=DeliverableFileReviewSerializer, responses=DeliverableFileSerializer)
    def post(self, request, file_id):
        deliverable_file = get_object_or_404(DeliverableFile, pk=file_id)
        serializer = DeliverableFileReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deliverable_file = DeliverableFileService.review_file(
            request.user,
            deliverable_file,
            serializer.validated_data["review_status"],
            serializer.validated_data.get("review_comment", ""),
        )
        return Response(DeliverableFileSerializer(deliverable_file).data, status=status.HTTP_200_OK)
