from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.assignments.models import Appeal, WishList
from apps.assignments.serializers import (
    AdminAppealReviewSerializer,
    AppealCreateSerializer,
    AppealSerializer,
    AssignmentRoundSerializer,
    ManualAssignmentSerializer,
    SubmitWishListSerializer,
    WishListDetailSerializer,
    WishListSerializer,
)
from apps.assignments.services import AppealService, AssignmentService, WishListService
from apps.campaigns.models import CampaignPhase
from apps.campaigns.services import CampaignPhaseService
from apps.teams.models import Team
from apps.teams.serializers import TeamDetailSerializer
from apps.teams.services import TeamService
from apps.topics.serializers import PublicSubjectSerializer
from config.pagination import DefaultPageNumberPagination


class AvailableSubjectCatalogView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Subjects Catalog"], responses=PublicSubjectSerializer(many=True))
    def get(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            queryset = WishListService.get_available_subjects_for_user_without_team()
        else:
            WishListService.ensure_catalog_open_for_team(team)
            queryset = WishListService.get_available_subjects_for_team(team).order_by("-created_at")

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(PublicSubjectSerializer(page, many=True).data)


class WishListSubmitView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Wishlists"], request=SubmitWishListSerializer, responses=WishListDetailSerializer)
    def post(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            return Response({"team": "You do not have an active team."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitWishListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wishlist = WishListService.submit_wishlist(
            team=team,
            actor=request.user,
            selection_round=serializer.validated_data["selection_round"],
            items=serializer.validated_data["items"],
        )
        return Response(WishListDetailSerializer(wishlist).data, status=status.HTTP_201_CREATED)


class MyWishListsView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Wishlists"], responses=WishListDetailSerializer(many=True))
    def get(self, request):
        team = TeamService.get_active_student_team(request.user)
        queryset = WishList.objects.none()
        if team is not None:
            queryset = WishList.objects.filter(team=team).prefetch_related("items__subject").order_by("created_at")
        return Response(WishListDetailSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class AppealSubmitView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Appeals"], request=AppealCreateSerializer, responses=AppealSerializer)
    def post(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            return Response({"team": "You do not have an active team."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AppealCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appeal = AppealService.submit_appeal(team, request.user, serializer.validated_data["reason"])
        return Response(AppealSerializer(appeal).data, status=status.HTTP_201_CREATED)


class MyAppealView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Appeals"], responses=AppealSerializer)
    def get(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            return Response({}, status=status.HTTP_200_OK)
        appeal = Appeal.objects.filter(team=team).first()
        if appeal is None:
            return Response({}, status=status.HTTP_200_OK)
        return Response(AppealSerializer(appeal).data, status=status.HTTP_200_OK)


class MyAssignmentResultView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Assignments"], responses=dict)
    def get(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            return Response({"team": "You do not have an active team."}, status=status.HTTP_400_BAD_REQUEST)
        if not CampaignPhaseService.is_open(team.academic_year, CampaignPhase.PhaseType.RESULTS_AND_APPEALS):
            return Response(
                {"detail": "Assignment results are not published for students at this time."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from apps.topics.models import Subject

        subject = Subject.objects.filter(assigned_to_team=team).first()
        return Response(
            {
                "team_code": team.pk,
                "team_status": team.status,
                "selection_round": team.selection_round,
                "subject_id": subject.id if subject else None,
                "subject_title": subject.title if subject else None,
            },
            status=status.HTTP_200_OK,
        )


class AdminWishListListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Wishlists"], responses=WishListSerializer(many=True))
    def get(self, request):
        queryset = WishList.objects.select_related("team", "academic_year", "submitted_by").order_by("-created_at")
        selection_round = request.query_params.get("selection_round")
        if selection_round:
            queryset = queryset.filter(selection_round=selection_round)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        team_code = request.query_params.get("team_code")
        if team_code:
            queryset = queryset.filter(team_id=team_code)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(WishListSerializer(page, many=True).data)


class AdminWishListDetailView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Wishlists"], responses=WishListDetailSerializer)
    def get(self, request, wishlist_id):
        wishlist = get_object_or_404(WishList.objects.prefetch_related("items__subject"), pk=wishlist_id)
        return Response(WishListDetailSerializer(wishlist).data, status=status.HTTP_200_OK)


class AdminMeritAssignmentView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Assignments"], request=AssignmentRoundSerializer)
    def post(self, request):
        serializer = AssignmentRoundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = AssignmentService.assign_by_merit(
            request.user,
            selection_round=serializer.validated_data["selection_round"],
            seed=serializer.validated_data.get("seed"),
        )
        return Response(summary, status=status.HTTP_200_OK)


class AdminRandomAssignmentView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Assignments"], request=AssignmentRoundSerializer)
    def post(self, request):
        serializer = AssignmentRoundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = AssignmentService.assign_randomly(
            request.user,
            selection_round=serializer.validated_data["selection_round"],
            seed=serializer.validated_data.get("seed"),
        )
        return Response(summary, status=status.HTTP_200_OK)


class AdminManualAssignmentView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Assignments"], request=ManualAssignmentSerializer)
    def post(self, request):
        serializer = ManualAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.get_team()
        subject = serializer.get_subject()
        if team is None:
            return Response({"team_code": "Team not found."}, status=status.HTTP_400_BAD_REQUEST)
        if subject is None:
            return Response({"subject_id": "Subject not found."}, status=status.HTTP_400_BAD_REQUEST)
        team = AssignmentService.manual_assign(request.user, team, subject)
        return Response({"team_code": team.pk, "subject_id": team.selected_subject.id}, status=status.HTTP_200_OK)


class AdminAssignmentValidateView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Assignments"], responses=TeamDetailSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        team = AssignmentService.validate_assignment(request.user, team)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class AdminAppealAcceptView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Appeals"], responses=AppealSerializer)
    def post(self, request, appeal_id):
        appeal = get_object_or_404(Appeal, pk=appeal_id)
        appeal = AppealService.accept_appeal(appeal, request.user)
        return Response(AppealSerializer(appeal).data, status=status.HTTP_200_OK)


class AdminAppealRejectView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Appeals"], request=AdminAppealReviewSerializer, responses=AppealSerializer)
    def post(self, request, appeal_id):
        appeal = get_object_or_404(Appeal, pk=appeal_id)
        serializer = AdminAppealReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appeal = AppealService.reject_appeal(
            appeal,
            request.user,
            admin_comment=serializer.validated_data.get("admin_comment", ""),
        )
        return Response(AppealSerializer(appeal).data, status=status.HTTP_200_OK)
