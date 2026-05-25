from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.campaigns.models import CampaignPhase
from apps.campaigns.serializers import CampaignPhaseSerializer
from apps.campaigns.services import CampaignPhaseService
from config.pagination import DefaultPageNumberPagination


class AdminCampaignPhaseListCreateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Campaign Phases"], responses=CampaignPhaseSerializer(many=True))
    def get(self, request):
        include_archived = request.query_params.get("include_archived", "false").lower()
        queryset = CampaignPhase.objects.select_related("academic_year")
        if include_archived != "true":
            queryset = queryset.filter(is_archived=False)

        academic_year = request.query_params.get("academic_year")
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)

        phase_type = request.query_params.get("phase_type")
        if phase_type:
            queryset = queryset.filter(phase_type=phase_type)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(
            queryset.order_by("academic_year_id", "display_order", "start_at"), request
        )
        serializer = CampaignPhaseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Campaign Phases"], request=CampaignPhaseSerializer, responses=CampaignPhaseSerializer)
    def post(self, request):
        serializer = CampaignPhaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phase = serializer.save()
        return Response(CampaignPhaseSerializer(phase).data, status=status.HTTP_201_CREATED)


class AdminCampaignPhaseDetailUpdateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Campaign Phases"], responses=CampaignPhaseSerializer)
    def get(self, request, pk):
        phase = get_object_or_404(CampaignPhase.objects.select_related("academic_year"), pk=pk)
        return Response(CampaignPhaseSerializer(phase).data)

    @extend_schema(tags=["Campaign Phases"], request=CampaignPhaseSerializer, responses=CampaignPhaseSerializer)
    def patch(self, request, pk):
        phase = get_object_or_404(CampaignPhase, pk=pk)
        if phase.is_archived:
            return Response(
                {"detail": "Archived campaign phase cannot be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if phase.academic_year.status != "ACTIVE":
            return Response(
                {"academic_year": "Campaign phases can be modified only for ACTIVE academic years."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CampaignPhaseSerializer(phase, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        phase = serializer.save()
        return Response(CampaignPhaseSerializer(phase).data)


class AdminCampaignPhaseArchiveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Campaign Phases"], responses={200: CampaignPhaseSerializer})
    def post(self, request, pk):
        phase = get_object_or_404(CampaignPhase, pk=pk)
        if phase.academic_year.status != "ACTIVE":
            return Response(
                {"academic_year": "Campaign phases can be modified only for ACTIVE academic years."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phase.is_archived = True
        phase.save(update_fields=["is_archived", "updated_at"])
        return Response(CampaignPhaseSerializer(phase).data, status=status.HTTP_200_OK)


class CurrentCampaignView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Campaign"], responses=dict)
    def get(self, request):
        return Response(CampaignPhaseService.get_user_action_availability(request.user), status=status.HTTP_200_OK)
