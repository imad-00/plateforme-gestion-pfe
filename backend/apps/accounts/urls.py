from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    IdentityAvailabilityView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestOTPView,
    PasswordResetResendOTPView,
    PasswordResetVerifyOTPView,
    RefreshView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "password-reset/request-otp/",
        PasswordResetRequestOTPView.as_view(),
        name="auth-password-reset-request-otp",
    ),
    path(
        "password-reset/resend-otp/",
        PasswordResetResendOTPView.as_view(),
        name="auth-password-reset-resend-otp",
    ),
    path(
        "password-reset/verify-otp/",
        PasswordResetVerifyOTPView.as_view(),
        name="auth-password-reset-verify-otp",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path(
        "identity-availability/",
        IdentityAvailabilityView.as_view(),
        name="auth-identity-availability",
    ),
]
