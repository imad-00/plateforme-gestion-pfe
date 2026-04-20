from rest_framework.permissions import BasePermission


def _is_active_account(user):
    if not user or not user.is_authenticated:
        return False
    # Source of truth is account_status.
    return getattr(user, "account_status", None) == "ACTIVE"


def get_platform_levels(user):
    """Resolve platform privilege from active PlatformAccessGrant only."""
    if not _is_active_account(user):
        return set()

    if hasattr(user, "platform_access_grants"):
        active_grants = list(
            user.platform_access_grants.filter(revoked_at__isnull=True).values_list(
                "access_level", flat=True
            )
        )
        if active_grants:
            return set(active_grants)
    return set()


class IsAuthenticatedAndActiveAccount(BasePermission):
    def has_permission(self, request, view):
        return _is_active_account(request.user)


class IsAuthenticatedAndNotArchived(IsAuthenticatedAndActiveAccount):
    """
    Backward-compatible alias used by existing endpoints/settings.
    """
    pass


class HasBusinessIdentity(BasePermission):
    allowed_identities = set()

    def has_permission(self, request, view):
        user = request.user
        if not _is_active_account(user):
            return False
        return user.business_identity in self.allowed_identities


class HasPlatformAccess(BasePermission):
    allowed_levels = set()

    def has_permission(self, request, view):
        return bool(get_platform_levels(request.user).intersection(self.allowed_levels))


class IsPlatformAdminOrSuperAdmin(HasPlatformAccess):
    allowed_levels = {"ADMIN", "SUPER_ADMIN"}


class IsPlatformSuperAdmin(HasPlatformAccess):
    allowed_levels = {"SUPER_ADMIN"}


class IsAdminOrSuperAdmin(IsPlatformAdminOrSuperAdmin):
    """Backward-compatible alias for existing API views."""
    pass


class IsSuperAdmin(IsPlatformSuperAdmin):
    """Backward-compatible alias for existing API views."""
    pass


class IsTeacherOrAbove(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not _is_active_account(user):
            return False

        business_identity = getattr(user, "business_identity", None)
        if business_identity == "TEACHER":
            return True

        return bool(get_platform_levels(user).intersection({"ADMIN", "SUPER_ADMIN"}))
