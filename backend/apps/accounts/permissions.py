from rest_framework.permissions import BasePermission


class IsAuthenticatedAndNotArchived(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            bool(user and user.is_authenticated)
            and user.is_active
            and not user.is_archived
        )


class HasGlobalRole(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        user = request.user
        if (
            not user
            or not user.is_authenticated
            or not user.is_active
            or user.is_archived
        ):
            return False
        return user.global_role in self.allowed_roles


class IsAdminOrSuperAdmin(HasGlobalRole):
    allowed_roles = {"ADMIN", "SUPER_ADMIN"}


class IsSuperAdmin(HasGlobalRole):
    allowed_roles = {"SUPER_ADMIN"}


class IsTeacherOrAbove(HasGlobalRole):
    allowed_roles = {"TEACHER", "ADMIN", "SUPER_ADMIN"}
