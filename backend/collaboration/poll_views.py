from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from trips.permissions import get_accessible_trip, get_user_trip

from .models import TripMembership, TripPoll, PollOption, PollVote
from .poll_serializers import (
    CreatePollSerializer,
    VoteSerializer,
    ClosePollSerializer,
)

User = get_user_model()


def eligible_user_ids(trip):
    return User.objects.filter(
        Q(pk=trip.owner_id)
        | Q(
            trip_memberships__trip=trip,
            trip_memberships__status=TripMembership.Status.ACCEPTED,
        )
    ).values("pk").distinct()


def poll_results(poll):
    counts = dict(
        poll.votes.filter(
            user_id__in=eligible_user_ids(poll.trip),
        )
        .values("option_id")
        .annotate(total=Count("id"))
        .values_list("option_id", "total")
    )

    options = [
        {
            "id": option.pk,
            "label": option.label,
            "votes": counts.get(option.pk, 0),
        }
        for option in poll.options.all()
    ]

    return {
        "total_votes": sum(item["votes"] for item in options),
        "options": options,
    }


def poll_data(poll, user):
    if poll.status == TripPoll.Status.CLOSED:
        results = poll.decision["results"]
    else:
        results = poll_results(poll)

    my_vote = (
        poll.votes.filter(user=user)
        .values_list("option_id", flat=True)
        .first()
    )

    return {
        "id": poll.pk,
        "trip": poll.trip_id,
        "title": poll.title,
        "category": poll.category,
        "status": poll.status,
        "created_at": poll.created_at,
        "closed_at": poll.closed_at,
        "my_vote": my_vote,
        **results,
        "decision": poll.decision or None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def trip_polls(request, trip_id):
    if request.method == "GET":
        trip = get_accessible_trip(request.user, trip_id)

        polls = (
            TripPoll.objects.filter(trip=trip)
            .select_related("trip")
            .prefetch_related("options")
        )

        return Response([
            poll_data(poll, request.user)
            for poll in polls
        ])

    trip = get_user_trip(request.user, trip_id)

    serializer = CreatePollSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = dict(serializer.validated_data)
    labels = data.pop("options")

    with transaction.atomic():
        poll = TripPoll.objects.create(
            trip=trip,
            **data,
        )

        PollOption.objects.bulk_create([
            PollOption(poll=poll, label=label)
            for label in labels
        ])

    return Response(
        poll_data(poll, request.user),
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def poll_detail(request, trip_id, poll_id):
    trip = get_accessible_trip(request.user, trip_id)

    poll = get_object_or_404(
        TripPoll,
        pk=poll_id,
        trip=trip,
    )

    return Response(poll_data(poll, request.user))


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def poll_vote(request, trip_id, poll_id):
    trip = get_accessible_trip(request.user, trip_id)

    serializer = VoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        poll = get_object_or_404(
            TripPoll.objects.select_for_update(),
            pk=poll_id,
            trip=trip,
        )

        if poll.status != TripPoll.Status.OPEN:
            raise ValidationError(
                "Esta votação já foi encerrada."
            )

        option = get_object_or_404(
            PollOption,
            pk=serializer.validated_data["option_id"],
            poll=poll,
        )

        PollVote.objects.update_or_create(
            poll=poll,
            user=request.user,
            defaults={"option": option},
        )

        result = poll_data(poll, request.user)

    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_poll(request, trip_id, poll_id):
    trip = get_user_trip(request.user, trip_id)

    serializer = ClosePollSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        poll = get_object_or_404(
            TripPoll.objects.select_for_update(),
            pk=poll_id,
            trip=trip,
        )

        if poll.status != TripPoll.Status.OPEN:
            raise ValidationError(
                "Esta votação já foi encerrada."
            )

        option = get_object_or_404(
            PollOption,
            pk=serializer.validated_data["option_id"],
            poll=poll,
        )

        results = poll_results(poll)

        if results["total_votes"] == 0:
            raise ValidationError(
                "É necessário pelo menos um voto para encerrar."
            )

        top = max(
            item["votes"]
            for item in results["options"]
        )

        chosen = next(
            item
            for item in results["options"]
            if item["id"] == option.pk
        )

        if chosen["votes"] != top:
            raise ValidationError(
                "Escolha a opção mais votada ou uma das empatadas "
                "na liderança."
            )

        poll.status = TripPoll.Status.CLOSED
        poll.closed_at = timezone.now()

        poll.decision = {
            "option_id": option.pk,
            "label": option.label,
            "reason": serializer.validated_data["reason"],
            "decided_by": request.user.pk,
            "results": results,
        }

        poll.save(update_fields=[
            "status",
            "closed_at",
            "decision",
        ])

        result = poll_data(poll, request.user)

    return Response(result)