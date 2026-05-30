from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount
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


class AdminTestEmailView(APIView):
    """Send a verification email to the calling admin using the active EMAIL
    backend. Bypasses Celery and the Notification pipeline — useful to prove
    SMTP works without faking a workflow event. Returns 200 on success with the
    delivery address; 502 with the error string on SMTP failure.
    """

    permission_classes = [IsAdminOrSuperAdmin]

    @extend_schema(tags=["Admin Notifications"])
    def post(self, request):
        recipient = (request.user.email or "").strip()
        if not recipient:
            return Response(
                {"detail": "Your account has no email address on file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = "GradeX email delivery test"
        message = (
            "This is a verification email triggered from the admin panel. "
            "If you can read this in your inbox, the platform's SMTP path is "
            "configured correctly and IMPORTANT notifications will be delivered."
        )
        plain_body = f"{message}\n\nSent by: {request.user.full_name} ({request.user.matricule})"
        html_body = render_to_string(
            "notifications/emails/notification.html",
            {
                "title": title,
                "message": message,
                "link_url": "",
                "is_important": False,
            },
        )

        try:
            email = EmailMultiAlternatives(
                subject=f"[PFE Platform] {title}",
                body=plain_body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                to=[recipient],
            )
            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)
        except Exception as exc:
            return Response(
                {"detail": f"SMTP send failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"detail": f"Test email sent to {recipient}."},
            status=status.HTTP_200_OK,
        )
