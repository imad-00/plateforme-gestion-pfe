from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
from apps.teams.models import Team, TeamParticipant
from apps.teams.serializers import (
    AddSupervisorSerializer,
    AdminRemoveMemberSerializer,
    InviteStudentSerializer,
    RemoveMemberSerializer,
    RemoveSupervisorSerializer,
    TeamDetailSerializer,
    TeamParticipantSerializer,
    TeamSerializer,
    TransferLeadershipSerializer,
)
from apps.teams.services import InvitationService, ParticipationService, TeamService
from config.pagination import DefaultPageNumberPagination


class MyTeamView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], responses=TeamDetailSerializer)
    def get(self, request):
        team = TeamService.get_active_student_team(request.user)
        if team is None:
            team = TeamService.create_solo_team_for_student(request.user)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class TeamInviteStudentView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], request=InviteStudentSerializer, responses=TeamParticipantSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = InviteStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.get_student()
        if student is None:
            return Response({"student": "Student not found."}, status=status.HTTP_400_BAD_REQUEST)
        participation = InvitationService.invite_student(team, student, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_201_CREATED)


class TeamInvitationAcceptView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], responses=TeamParticipantSerializer)
    def post(self, request, participation_id):
        participation = get_object_or_404(TeamParticipant, pk=participation_id)
        participation = InvitationService.accept_invitation(participation, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class TeamInvitationRejectView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], responses=TeamParticipantSerializer)
    def post(self, request, participation_id):
        participation = get_object_or_404(TeamParticipant, pk=participation_id)
        participation = InvitationService.reject_invitation(participation, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class LeaveTeamView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], responses=TeamParticipantSerializer)
    def post(self, request):
        participation = ParticipationService.leave_team(request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class TeamRemoveMemberView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], request=RemoveMemberSerializer, responses=TeamParticipantSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = RemoveMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.get_student()
        if student is None:
            return Response({"student": "Student not found."}, status=status.HTTP_400_BAD_REQUEST)
        participation = ParticipationService.remove_member(team, student, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class TeamTransferLeadershipView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], request=TransferLeadershipSerializer, responses=TeamDetailSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = TransferLeadershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_leader = serializer.get_new_leader()
        if new_leader is None:
            return Response({"new_leader_id": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        team = ParticipationService.transfer_leadership(team, new_leader, request.user)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class TeamLockView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Teams"], responses=TeamDetailSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        team = TeamService.lock_team(team, request.user)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class AdminTeamListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], responses=TeamSerializer(many=True))
    def get(self, request):
        queryset = Team.objects.select_related("academic_year").order_by("-created_at")
        academic_year = request.query_params.get("academic_year")
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        paginator = DefaultPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(TeamSerializer(page, many=True).data)


class AdminTeamDetailView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], responses=TeamDetailSerializer)
    def get(self, request, team_code):
        team = get_object_or_404(Team.objects.select_related("academic_year"), pk=team_code)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class AdminTeamRemoveMemberView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], request=AdminRemoveMemberSerializer, responses=TeamParticipantSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = AdminRemoveMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.get_student()
        if student is None:
            return Response({"student_id": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        new_leader = serializer.get_new_leader()
        participation = ParticipationService.admin_remove_member(
            team,
            student,
            request.user,
            new_leader_user=new_leader,
            dissolve_if_needed=serializer.validated_data.get("dissolve_if_needed", False),
        )
        if isinstance(participation, Team):
            return Response(TeamDetailSerializer(participation).data, status=status.HTTP_200_OK)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class AdminTeamTransferLeadershipView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], request=TransferLeadershipSerializer, responses=TeamDetailSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = TransferLeadershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_leader = serializer.get_new_leader()
        if new_leader is None:
            return Response({"new_leader_id": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        team = ParticipationService.transfer_leadership(team, new_leader, request.user, admin_override=True)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)


class AdminTeamSupervisorAddView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], request=AddSupervisorSerializer, responses=TeamParticipantSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = AddSupervisorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supervisor = serializer.get_user()
        if supervisor is None:
            return Response({"user_id": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        participation = ParticipationService.add_supervisor(team, supervisor, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_201_CREATED)


class AdminTeamSupervisorRemoveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], request=RemoveSupervisorSerializer, responses=TeamParticipantSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        serializer = RemoveSupervisorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supervisor = serializer.get_user()
        if supervisor is None:
            return Response({"user_id": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        participation = ParticipationService.remove_supervisor(team, supervisor, request.user)
        return Response(TeamParticipantSerializer(participation).data, status=status.HTTP_200_OK)


class AdminTeamDissolveView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Teams"], responses=TeamDetailSerializer)
    def post(self, request, team_code):
        team = get_object_or_404(Team, pk=team_code)
        team = TeamService.dissolve_team(team, actor=request.user)
        return Response(TeamDetailSerializer(team).data, status=status.HTTP_200_OK)
