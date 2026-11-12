from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    parser_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    ProfilePhotoSerializer,
)

import mimetypes

from django.http import FileResponse
from rest_framework.exceptions import NotFound


User = get_user_model()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        user = serializer.save()
        token = Token.objects.create(user=user)

    return Response(
        {
            "user": UserSerializer(user).data,
            "token": token.key,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data

    account = User.objects.filter(
        email__iexact=data["email"],
    ).first()

    user = authenticate(
        request=request,
        username=(
            account.get_username()
            if account
            else data["email"]
        ),
        password=data["password"],
    )

    if account is None or user is None:
        return Response(
            {
                "detail": "E-mail ou senha inválidos.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "user": UserSerializer(user).data,
        "token": token.key,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    request.auth.delete()

    return Response({
        "detail": "Logout realizado com sucesso.",
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "PATCH":
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

    return Response(
        ProfileSerializer(
            request.user,
            context={"request": request},
        ).data
    )

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def profile_photo(request):
    user = request.user

    if request.method == "GET":
        if not user.photo:
            raise NotFound()

        content_type, _ = mimetypes.guess_type(
            user.photo.name
        )

        response = FileResponse(
            user.photo.open("rb"),
            content_type=(
                content_type
                or "application/octet-stream"
            ),
        )

        response["Cache-Control"] = "private, no-store"

        return response

    if request.method == "DELETE":
        if user.photo:
            user.photo.delete(save=True)

    else:
        serializer = ProfilePhotoSerializer(
            user,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        old_photo = user.photo.name

        serializer.save()

        if old_photo and old_photo != user.photo.name:
            user.photo.storage.delete(old_photo)

    return Response(
        ProfileSerializer(
            user,
            context={"request": request},
        ).data
    )