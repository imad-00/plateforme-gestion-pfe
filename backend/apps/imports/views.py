from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.imports.models import UserImportBatch
from apps.imports.serializers import (
    UserImportBatchSerializer,
    UserImportConfirmSerializer,
    UserImportPreviewSerializer,
)
from apps.imports.services import UserImportService


class UserImportPreviewView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Admin Imports"], request=UserImportPreviewSerializer, responses=UserImportBatchSerializer)
    def post(self, request):
        serializer = UserImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = UserImportService.preview_user_import(
            request.user,
            serializer.validated_data["file"],
            serializer.validated_data["import_type"],
            request=request,
        )
        return Response(UserImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class UserImportConfirmView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Imports"], request=UserImportConfirmSerializer)
    def post(self, request):
        serializer = UserImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = get_object_or_404(UserImportBatch, pk=serializer.validated_data["batch_id"])
        result = UserImportService.confirm_user_import(
            request.user,
            batch,
            confirm=serializer.validated_data["confirm"],
            allow_partial=serializer.validated_data["allow_partial"],
            request=request,
        )
        return Response(
            {
                "batch": UserImportBatchSerializer(result["batch"]).data,
                "created_count": result["created_count"],
                "skipped_count": result["skipped_count"],
                "error_count": result["error_count"],
                "created_users": result["created_users"],
            },
            status=status.HTTP_200_OK,
        )


class UserImportTemplateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Imports"])
    def get(self, request):
        return UserImportService.generate_template(request.query_params.get("import_type"))
