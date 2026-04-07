from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class MatriculeOrEmailBackend(ModelBackend):
    """Authenticate users with either matricule or email."""

    def authenticate(self, request, username=None, password=None, identifier=None, **kwargs):
        user_model = get_user_model()
        identifier = identifier or username or kwargs.get(user_model.USERNAME_FIELD)

        if not identifier or not password:
            return None

        user = (
            user_model.objects.filter(
                Q(email__iexact=identifier) | Q(matricule__iexact=identifier)
            )
            .order_by("id")
            .first()
        )

        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.is_archived
