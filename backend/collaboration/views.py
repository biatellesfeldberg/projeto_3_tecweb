from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Friendship
from .serializers import (
    FriendshipSerializer,
    PublicUserSerializer,
    SendFriendRequestSerializer,
)


User = get_user_model()


def user_friendships(user):
    return Friendship.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).select_related(
        "sender",
        "recipient",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_search(request):
    search = request.query_params.get(
        "search",
        "",
    ).strip()

    if len(search) < 2:
        return Response([])

    users = User.objects.filter(
        is_active=True,
    ).exclude(
        pk=request.user.pk,
    )

    users = users.filter(
        Q(first_name__icontains=search)
        | Q(last_name__icontains=search)
        | Q(email__iexact=search)
    ).order_by(
        "first_name",
        "last_name",
        "id",
    )[:20]

    return Response(
        PublicUserSerializer(users, many=True).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def friend_list(request):
    links = user_friendships(request.user).filter(
        status=Friendship.Status.ACCEPTED,
    )

    friends = [
        (
            link.recipient
            if link.sender_id == request.user.pk
            else link.sender
        )
        for link in links
    ]

    return Response(
        PublicUserSerializer(friends, many=True).data
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def friend_request_list(request):
    if request.method == "GET":
        pending = user_friendships(request.user).filter(
            status=Friendship.Status.PENDING,
        )

        return Response({
            "received": FriendshipSerializer(
                pending.filter(recipient=request.user),
                many=True,
            ).data,
            "sent": FriendshipSerializer(
                pending.filter(sender=request.user),
                many=True,
            ).data,
        })

    serializer = SendFriendRequestSerializer(
        data=request.data,
        context={"request": request},
    )

    serializer.is_valid(raise_exception=True)

    try:
        with transaction.atomic():
            link = Friendship.objects.create(
                sender=request.user,
                recipient_id=(
                    serializer.validated_data["recipient_id"]
                ),
            )
    except IntegrityError:
        raise ValidationError({
            "recipient_id": [
                "Não foi possível enviar. Verifique se já existe "
                "uma solicitação ou amizade entre vocês."
            ],
        })

    return Response(
        FriendshipSerializer(link).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_friend_request(request, request_id):
    updated = Friendship.objects.filter(
        pk=request_id,
        recipient=request.user,
        status=Friendship.Status.PENDING,
    ).update(
        status=Friendship.Status.ACCEPTED,
        updated_at=timezone.now(),
    )

    if not updated:
        raise NotFound()

    return Response({
        "detail": "Solicitação aceita.",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_friend_request(request, request_id):
    deleted, _ = Friendship.objects.filter(
        pk=request_id,
        recipient=request.user,
        status=Friendship.Status.PENDING,
    ).delete()

    if not deleted:
        raise NotFound()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_friend_request(request, request_id):
    deleted, _ = Friendship.objects.filter(
        pk=request_id,
        sender=request.user,
        status=Friendship.Status.PENDING,
    ).delete()

    if not deleted:
        raise NotFound()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_friend(request, user_id):
    deleted, _ = Friendship.objects.filter(
        Q(
            sender=request.user,
            recipient_id=user_id,
        )
        | Q(
            recipient=request.user,
            sender_id=user_id,
        ),
        status=Friendship.Status.ACCEPTED,
    ).delete()

    if not deleted:
        raise NotFound()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )