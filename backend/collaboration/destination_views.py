from copy import deepcopy
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from trips.models import Trip
from trips.permissions import (
    get_accessible_trip,
    get_manageable_trip,
    trip_participants,
)

from .destination_serializers import RecommendationRequestSerializer

from .destinations import (
    WEIGHTS,
    collect_context,
    components_for,
    generate_recommendations,
    require_complete,
)

from .models import GroupDestinationRecommendation


class GroupChangedError(APIException):
    status_code = 409

    default_detail = (
        "O grupo ou suas respostas mudaram. "
        "Gere a recomendação novamente."
    )


def result_data(record, trip):
    context = collect_context(
        trip,
        record.origin_country_code,
    )

    stale = context["fingerprint"] != record.fingerprint
    result = None

    if not stale:
        result = deepcopy(record.result)

        members = list(
            trip_participants(trip).order_by("pk")
        )

        if len(members) != len(context["profiles"]):
            raise GroupChangedError()

        candidates = [
            result["recommendation"],
            *result["alternatives"],
        ]

        for candidate in candidates:
            features = {
                **candidate,
                "cost_max": Decimal(
                    candidate["estimated_cost_per_person"]["max"]
                ),
            }

            individual = []

            for member, profile in zip(
                members,
                context["profiles"],
            ):
                components = components_for(
                    profile,
                    features,
                    trip,
                    record.origin_country_code,
                )

                score = round(
                    sum(
                        components[key] * weight
                        for key, weight in WEIGHTS.items()
                    ),
                    1,
                )

                individual.append({
                    "user": {
                        "id": member.pk,
                        "first_name": member.first_name,
                        "last_name": member.last_name,
                    },
                    "score": score,
                    "label": (
                        "high"
                        if score >= 80
                        else "medium"
                        if score >= 60
                        else "low"
                    ),
                })

            candidate["compatibility"]["members"] = individual

    return {
        "available": not stale,
        "stale": stale,
        "generated_at": record.generated_at.isoformat(),
        "result": result,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def group_destinations(request, trip_id):
    get_trip = (
        get_accessible_trip
        if request.method == "GET"
        else get_manageable_trip
    )

    trip = get_trip(
        request.user,
        trip_id,
    )

    if request.method == "GET":
        record = (
            GroupDestinationRecommendation.objects
            .filter(trip=trip)
            .first()
        )

        if record is None:
            return Response({
                "available": False,
                "stale": False,
                "generated_at": None,
                "result": None,
            })

        return Response(result_data(record, trip))

    serializer = RecommendationRequestSerializer(
        data=request.data
    )

    serializer.is_valid(raise_exception=True)

    country = serializer.validated_data[
        "origin_country_code"
    ]

    context = collect_context(
        trip,
        country,
    )

    require_complete(
        trip,
        context,
    )

    record = (
        GroupDestinationRecommendation.objects
        .filter(trip=trip)
        .first()
    )

    if (
        record
        and record.fingerprint == context["fingerprint"]
        and not serializer.validated_data["refresh"]
    ):
        return Response(result_data(record, trip))

    result = generate_recommendations(
        trip,
        context,
        country,
    )

    with transaction.atomic():
        trip = get_object_or_404(
            Trip.objects.select_for_update(),
            pk=trip.pk,
        )

        get_manageable_trip(
            request.user,
            trip.pk,
        )

        current_context = collect_context(
            trip,
            country,
        )

        if (
            current_context["fingerprint"]
            != context["fingerprint"]
        ):
            raise GroupChangedError()

        record, _ = (
            GroupDestinationRecommendation.objects
            .update_or_create(
                trip=trip,
                defaults={
                    "fingerprint": context["fingerprint"],
                    "origin_country_code": country,
                    "result": result,
                },
            )
        )

    return Response(result_data(record, trip))