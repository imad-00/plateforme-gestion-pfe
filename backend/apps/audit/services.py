from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import get_platform_levels
from apps.audit.models import AdminActionLog


class AdminActionLogService:
    @staticmethod
    def _is_super_admin(user):
        return "SUPER_ADMIN" in get_platform_levels(user)

    @staticmethod
    def _request_metadata(request):
        if request is None:
            return "", ""
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        return ip_address, user_agent

    @staticmethod
    def _target_from_object(target):
        if target is None:
            return "", "", ""
        meta = getattr(target, "_meta", None)
        target_model = meta.label if meta else target.__class__.__name__
        return target_model, str(getattr(target, "pk", "") or ""), str(target)[:255]

    @staticmethod
    def log(
        actor,
        action_type,
        target=None,
        target_model=None,
        target_id=None,
        target_repr=None,
        metadata=None,
        request=None,
    ):
        resolved_model, resolved_id, resolved_repr = AdminActionLogService._target_from_object(target)
        ip_address, user_agent = AdminActionLogService._request_metadata(request)
        return AdminActionLog.objects.create(
            actor=actor,
            action_type=action_type,
            target_model=target_model if target_model is not None else resolved_model,
            target_id=str(target_id) if target_id is not None else resolved_id,
            target_repr=(target_repr if target_repr is not None else resolved_repr)[:255],
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def list_logs(actor, filters=None):
        if not AdminActionLogService._is_super_admin(actor):
            raise PermissionDenied("Only super admins can view admin action logs.")
        filters = filters or {}
        queryset = AdminActionLog.objects.select_related("actor").order_by("-occurred_at", "-id")
        if filters.get("action_type"):
            queryset = queryset.filter(action_type=filters["action_type"])
        if filters.get("actor_id"):
            queryset = queryset.filter(actor_id=filters["actor_id"])
        if filters.get("target_model"):
            queryset = queryset.filter(target_model=filters["target_model"])
        if filters.get("date_from"):
            parsed = parse_datetime(filters["date_from"])
            if parsed is not None:
                queryset = queryset.filter(occurred_at__gte=parsed)
        if filters.get("date_to"):
            parsed = parse_datetime(filters["date_to"])
            if parsed is not None:
                queryset = queryset.filter(occurred_at__lte=parsed)
        return queryset
