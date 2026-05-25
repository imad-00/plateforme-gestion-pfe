from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestOTPSerializer,
    PasswordResetResendOTPSerializer,
    PasswordResetVerifyOTPSerializer,
    ChangePasswordSerializer,
    IdentityAvailabilitySerializer,
    RefreshTokenInputSerializer,
    UserSerializer,
)
from apps.accounts.permissions import IsAdminOrSuperAdmin, IsAuthenticatedAndActiveAccount


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="JWT tokens + user payload")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RefreshTokenInputSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(
        responses={200: UserSerializer},
        tags=["Auth"],
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description="Refresh token blacklisted.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)


class PasswordResetRequestOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=PasswordResetRequestOTPSerializer,
        responses={200: OpenApiResponse(description="OTP request accepted.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = PasswordResetRequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class PasswordResetResendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=PasswordResetResendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP resent if account is active.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = PasswordResetResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class PasswordResetVerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=PasswordResetVerifyOTPSerializer,
        responses={200: OpenApiResponse(description="OTP verification completed.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = PasswordResetVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset confirmed.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class IdentityAvailabilityView(APIView):
    permission_classes = [IsAuthenticatedAndActiveAccount, IsAdminOrSuperAdmin]

    @extend_schema(
        request=IdentityAvailabilitySerializer,
        responses={200: OpenApiResponse(description="Identity availability returned.")},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = IdentityAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)
