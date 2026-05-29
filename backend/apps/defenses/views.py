import json

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.defenses.models import Defense, DefenseAttachedFile, DefenseSupervisorDecision
from apps.defenses.serializers import (
    DefenseAttachedFileSerializer,
    DefenseDetailSerializer,
    DefenseRequestSerializer,
    DefenseSerializer,
    RescheduleDefenseSerializer,
    ScheduleDefenseSerializer,
    UpdateDefenseFilesSerializer,
    UpdateJurySerializer,
    UploadPVSerializer,
)
from apps.defenses.services import DefenseService
from config.pagination import DefaultPageNumberPagination


def _extract_list(request, key):
    values = request.data.getlist(key) if hasattr(request.data, "getlist") else None
    if values:
        if len(values) == 1:
            raw = values[0]
            if isinstance(raw, str) and raw.startswith("["):
                return json.loads(raw)
        return values
    raw = request.data.get(key)
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.startswith("["):
        return json.loads(raw)
    return [raw]


class DefenseRequestView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Defenses"], request=DefenseRequestSerializer, responses=DefenseDetailSerializer)
    def post(self, request):
        serializer = DefenseRequestSerializer(
            data={
                "existing_file_ids": _extract_list(request, "existing_file_ids"),
                "ordering": _extract_list(request, "ordering"),
            }
        )
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.request_defense(
            request.user,
            existing_file_ids=serializer.validated_data.get("existing_file_ids", []),
            uploaded_files=request.FILES.getlist("files"),
            ordering=serializer.validated_data.get("ordering", []),
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_201_CREATED)


class MyDefenseView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Defenses"], responses=DefenseDetailSerializer)
    def get(self, request):
        defense = DefenseService.list_my_defense(request.user)
        if defense is None:
            return Response({}, status=status.HTTP_200_OK)
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class DefenseFilesView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Defenses"], responses=DefenseAttachedFileSerializer(many=True))
    def get(self, request, defense_id):
        defense = get_object_or_404(Defense.objects.select_related("team"), pk=defense_id)
        if not DefenseService.can_access_defense_files(request.user, defense):
            return Response({"detail": "You do not have access to these defense files."}, status=status.HTTP_403_FORBIDDEN)
        files = defense.attached_files.select_related("deliverable_file", "added_by").order_by("order")
        return Response(DefenseAttachedFileSerializer(files, many=True).data, status=status.HTTP_200_OK)


class SupervisorDefenseRequestListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], responses=DefenseSerializer(many=True))
    def get(self, request):
        queryset = DefenseService.list_supervisor_requests(request.user)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DefenseSerializer(page, many=True).data)


class DefenseAcceptView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        defense = DefenseService.decide_supervisor(defense, request.user, DefenseSupervisorDecision.DecisionStatus.ACCEPTED)
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class DefenseDenyView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Supervision"], responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        defense = DefenseService.decide_supervisor(defense, request.user, DefenseSupervisorDecision.DecisionStatus.DENIED)
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class JuryDefenseListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Jury"], responses=DefenseSerializer(many=True))
    def get(self, request):
        queryset = DefenseService.list_jury_defenses(request.user)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DefenseSerializer(page, many=True).data)


class JuryDefenseDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Jury"], responses=DefenseDetailSerializer)
    def get(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        if not DefenseService.can_access_defense_files(request.user, defense):
            return Response({"detail": "You do not have access to this defense."}, status=status.HTTP_403_FORBIDDEN)
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class JuryDefenseFilesView(DefenseFilesView):
    pass


class JuryUploadPVView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Jury"], request=UploadPVSerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = UploadPVSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.upload_pv(
            request.user,
            defense,
            serializer.validated_data["final_grade"],
            serializer.validated_data["deliberation"],
            serializer.validated_data["pv_file"],
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminDefenseListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Defenses"], responses=DefenseSerializer(many=True))
    def get(self, request):
        queryset = Defense.objects.select_related("team", "requested_by", "scheduled_by", "pv_uploaded_by").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        academic_year = request.query_params.get("academic_year")
        if academic_year:
            queryset = queryset.filter(team__academic_year_id=academic_year)
        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(DefenseSerializer(page, many=True).data)


class AdminDefenseDetailView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Defenses"], responses=DefenseDetailSerializer)
    def get(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminScheduleDefenseView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Defenses"], request=ScheduleDefenseSerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = ScheduleDefenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.schedule_defense(
            request.user,
            defense,
            serializer.validated_data["scheduled_at"],
            serializer.validated_data.get("location", ""),
            serializer.get_president_user(),
            serializer.get_examiner_users(),
            guest_users=serializer.get_guest_users(),
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminRescheduleDefenseView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Defenses"], request=RescheduleDefenseSerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = RescheduleDefenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.reschedule_defense(
            request.user,
            defense,
            scheduled_at=serializer.validated_data.get("scheduled_at"),
            location=serializer.validated_data.get("location"),
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminUpdateJuryView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Defenses"], request=UpdateJurySerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = UpdateJurySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.update_jury(
            request.user,
            defense,
            serializer.get_president_user(),
            serializer.get_examiner_users(),
            guest_users=serializer.get_guest_users(),
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminUpdateDefenseFilesView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Admin Defenses"], request=UpdateDefenseFilesSerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = UpdateDefenseFilesSerializer(
            data={
                "existing_file_ids": _extract_list(request, "existing_file_ids"),
                "remove_ids": _extract_list(request, "remove_ids"),
                "ordering": _extract_list(request, "ordering"),
            }
        )
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.update_attached_files(
            request.user,
            defense,
            existing_file_ids=serializer.validated_data.get("existing_file_ids", []),
            uploaded_files=request.FILES.getlist("files"),
            remove_ids=serializer.validated_data.get("remove_ids", []),
            ordering=serializer.validated_data.get("ordering", []),
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)


class AdminUploadPVView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Admin Defenses"], request=UploadPVSerializer, responses=DefenseDetailSerializer)
    def post(self, request, defense_id):
        defense = get_object_or_404(Defense, pk=defense_id)
        serializer = UploadPVSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        defense = DefenseService.upload_pv(
            request.user,
            defense,
            serializer.validated_data["final_grade"],
            serializer.validated_data["deliberation"],
            serializer.validated_data["pv_file"],
        )
        return Response(DefenseDetailSerializer(defense).data, status=status.HTTP_200_OK)
