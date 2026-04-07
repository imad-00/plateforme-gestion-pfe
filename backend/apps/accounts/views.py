from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.serializers import (
    LoginSerializer,
    RefreshTokenInputSerializer,
    UserSerializer,
)
from apps.accounts.permissions import IsAuthenticatedAndNotArchived


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
    permission_classes = [IsAuthenticatedAndNotArchived]

    @extend_schema(
        responses={200: UserSerializer},
        tags=["Auth"],
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
