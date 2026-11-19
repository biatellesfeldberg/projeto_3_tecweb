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
)

from .destination_serializers import (
    RecommendationRequestSerializer,
)

from .destinations import (
    collect_context,
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


def result_data(record, stale=False):
    return {
        "available": not stale,
        "stale": stale,
        "generated_at": record.generated_at.isoformat(),
        "result": None if stale else record.result,
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

        context = collect_context(
            trip,
            record.origin_country_code,
        )

        return Response(
            result_data(
                record,
                stale=(
                    context["fingerprint"]
                    != record.fingerprint
                ),
            )
        )

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
        return Response(result_data(record))

    result = generate_recommendations(
        trip,
        context,
        country,
    )

    with transaction.atomic():
        # A espera pela IA ocorre antes da transação.
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

    return Response(result_data(record))