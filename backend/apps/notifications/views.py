from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndActiveAccount
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer, UnreadCountSerializer
from apps.notifications.services import NotificationService


class NotificationListView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Notifications"], responses=NotificationSerializer(many=True))
    def get(self, request):
        queryset = NotificationService.list_for_user(request.user)
        if request.query_params.get("unread", "").lower() == "true":
            queryset = queryset.filter(is_read=False)
        limit = request.query_params.get("limit")
        offset = int(request.query_params.get("offset") or 0)
        if limit is not None:
            queryset = queryset[offset : offset + int(limit)]
        elif offset:
            queryset = queryset[offset:]
        return Response(NotificationSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Notifications"], responses=UnreadCountSerializer)
    def get(self, request):
        return Response(
            {"unread_count": NotificationService.unread_count(request.user)},
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Notifications"], responses=NotificationSerializer)
    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, pk=notification_id)
        notification = NotificationService.mark_read(request.user, notification)
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(tags=["Notifications"])
    def post(self, request):
        updated = NotificationService.mark_all_read(request.user)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
