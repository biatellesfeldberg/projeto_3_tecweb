from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .calculator import duration_for_budget, estimate_for_duration
from .itinerary import generate_itinerary, suggest_destinations
from .replanning import (
    apply_proposal,
    compare_day,
    create_proposal,
    discard_proposal,
    is_outdated,
)
from .models import ItineraryProposal, Trip
from .permissions import (
    get_user_activity,
    get_user_day,
    get_user_trip,
    trips_for_user,
    accessible_trips_for_user,
    get_accessible_trip,
    get_manageable_trip,
    trip_role,
)
from .serializers import (
    ActivitySerializer,
    CostCalculatorSerializer,
    DestinationSuggestionsSerializer,
    GenerateItinerarySerializer,
    ReorderSerializer,
    ReplanSerializer,
    TripDaySerializer,
    TripDayUpdateSerializer,
    TripDetailSerializer,
    TripSummarySerializer,
    TripWriteSerializer,
)
from .services import (
    apply_profile_preferences,
    duplicate_trip,
    next_activity_order,
    sync_days,
    trip_with_itinerary,
)


def _trip_detail_response(request, trip_id, response_status=status.HTTP_200_OK):
    # Recarrega a viagem com dias e atividades já ordenados.
    trip = trip_with_itinerary(
        accessible_trips_for_user(request.user)
    ).get(id=trip_id)
    return Response(TripDetailSerializer(trip).data, status=response_status)


# ---------------------------------------------------------------------------
# Viagens
# ---------------------------------------------------------------------------


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def trip_list(request):
    if request.method == "POST":
        data = apply_profile_preferences(request.user, request.data.copy())
        serializer = TripWriteSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # O dono é sempre quem está logado, nunca um valor enviado.
            trip = serializer.save(owner=request.user)
            sync_days(trip)

        return _trip_detail_response(
            request, trip.id, response_status=status.HTTP_201_CREATED
        )

    trips = accessible_trips_for_user(request.user)

    trip_status = request.query_params.get("status", "").strip()
    if trip_status:
        if trip_status not in Trip.Status.values:
            raise ValidationError(
                {"status": [f'"{trip_status}" não é uma escolha válida.']}
            )
        trips = trips.filter(status=trip_status)

    return Response(TripSummarySerializer(trips, many=True).data)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def trip_detail(request, trip_id):
    if request.method == "GET":
        trip = get_accessible_trip(
            request.user,
            trip_id,
        )
    else:
        trip = get_user_trip(
            request.user,
            trip_id,
        )

    if request.method == "DELETE":
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PATCH":
        serializer = TripWriteSerializer(trip, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            trip = serializer.save()
            if {"start_date", "end_date"} & set(serializer.validated_data):
                sync_days(trip)

    return _trip_detail_response(request, trip.id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trip_duplicate(request, trip_id):
    trip = get_user_trip(request.user, trip_id)
    new_trip = duplicate_trip(trip)

    return _trip_detail_response(
        request, new_trip.id, response_status=status.HTTP_201_CREATED
    )


# ---------------------------------------------------------------------------
# Geração com IA
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trip_generate_itinerary(request, trip_id):
    trip = get_user_trip(request.user, trip_id)

    serializer = GenerateItinerarySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    options = serializer.validated_data

    if not trip.destination:
        raise ValidationError({
            "destination": ["Escolha um destino antes de gerar o roteiro."],
        })

    has_empty_day = trip.days.filter(activities__isnull=True).exists()

    # Sem dias vazios para preencher, não há o que pedir à IA.
    if options["replace_existing"] or has_empty_day:
        generate_itinerary(
            trip,
            replace_existing=options["replace_existing"],
            extra_instructions=options["extra_instructions"],
        )

    return _trip_detail_response(request, trip.id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trip_destination_suggestions(request, trip_id):
    trip = get_user_trip(request.user, trip_id)

    serializer = DestinationSuggestionsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    suggestions = suggest_destinations(
        trip,
        extra_instructions=serializer.validated_data["extra_instructions"],
    )

    return Response({"suggestions": suggestions})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trip_cost_calculator(request, trip_id):
    # Só faz contas e guarda os valores de referência da IA, sem mudar o
    # roteiro. Por isso integrantes da viagem também podem usar.
    trip = get_accessible_trip(request.user, trip_id)

    serializer = CostCalculatorSerializer(
        data=request.data,
        context={"trip": trip},
    )
    serializer.is_valid(raise_exception=True)
    options = serializer.validated_data

    if not trip.destination:
        raise ValidationError({
            "destination": ["Escolha um destino antes de calcular os custos."],
        })

    if options["mode"] == CostCalculatorSerializer.Mode.DURATION:
        result = estimate_for_duration(
            trip,
            options["days"],
            options["style"],
            refresh=options["refresh"],
        )
    else:
        result = duration_for_budget(
            trip,
            options["budget"],
            options["style"],
            refresh=options["refresh"],
        )

    return Response(result)


# ---------------------------------------------------------------------------
# Replanejamento (propostas de ajuste do roteiro)
# ---------------------------------------------------------------------------


def _person(user):
    if user is None:
        return None
    name = f"{user.first_name} {user.last_name}".strip()
    return {"id": user.id, "name": name or user.email}


def _proposal_data(proposal, user):
    trip = proposal.trip
    content = proposal.proposal
    pending = proposal.status == ItineraryProposal.Status.PENDING
    outdated = pending and is_outdated(proposal)
    role = trip_role(user, trip)

    current_days = {
        day.id: day
        for day in trip.days.prefetch_related("activities__day__trip")
    }

    days = []
    for proposed in content["days"]:
        day = current_days.get(proposed["day_id"])
        current = list(day.activities.all()) if day else []
        comparison = compare_day(
            [activity.title for activity in current],
            [activity["title"] for activity in proposed["activities"]],
        )
        days.append({
            "day_id": proposed["day_id"],
            "day_number": proposed["day_number"],
            "date": day.date if day else None,
            "current_title": day.title if day else "",
            "proposed_title": proposed["title"],
            "current": ActivitySerializer(current, many=True).data,
            "proposed": proposed["activities"],
            **comparison,
            "changed": bool(comparison["added"] or comparison["removed"])
            or (day is not None and proposed["title"] != day.title),
        })

    return {
        "id": proposal.id,
        "trip": trip.id,
        "status": proposal.status,
        "request": proposal.request,
        "place_ids": proposal.place_ids,
        "created_by": _person(proposal.created_by),
        "created_at": proposal.created_at,
        "decided_by": _person(proposal.decided_by),
        "decided_at": proposal.decided_at,
        "summary": content.get("summary", ""),
        "changes": content.get("changes", []),
        "decisions": content.get("decisions", []),
        "warnings": content.get("warnings", []),
        "days": days,
        "estimates": content.get("estimates", {}),
        "current_estimate": trip.cost_estimate,
        "is_outdated": outdated,
        "can_apply": pending and not outdated and role == "owner",
        "can_discard": pending
        and (role == "owner" or proposal.created_by_id == user.id),
    }


def _get_proposal(trip, proposal_id):
    proposal = trip.proposals.filter(id=proposal_id).first()
    if proposal is None:
        raise NotFound()
    return proposal


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def proposal_list(request, trip_id):
    # Organizadora e integrantes podem pedir e ver propostas. Só a
    # organizadora aplica (proposal_apply).
    trip = get_accessible_trip(request.user, trip_id)

    if request.method == "GET":
        pending = trip.proposals.filter(
            status=ItineraryProposal.Status.PENDING
        ).first()
        return Response({
            "proposal": _proposal_data(pending, request.user) if pending else None,
        })

    serializer = ReplanSerializer(
        data=request.data,
        context={"trip": trip, "user": request.user},
    )
    serializer.is_valid(raise_exception=True)
    options = serializer.validated_data

    if not trip.destination:
        raise ValidationError({
            "destination": ["Escolha um destino antes de ajustar o roteiro."],
        })

    if not trip.days.exists():
        raise ValidationError({
            "day_ids": ["Esta viagem ainda não tem dias."],
        })

    proposal = create_proposal(
        trip,
        request.user,
        request=options["request"],
        places=options["place_ids"],
        editable_days=options["day_ids"],
    )

    return Response(
        _proposal_data(proposal, request.user),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proposal_detail(request, trip_id, proposal_id):
    trip = get_accessible_trip(request.user, trip_id)
    proposal = _get_proposal(trip, proposal_id)
    return Response(_proposal_data(proposal, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def proposal_apply(request, trip_id, proposal_id):
    trip = get_manageable_trip(request.user, trip_id)
    proposal = apply_proposal(_get_proposal(trip, proposal_id), request.user)

    proposal.refresh_from_db()
    detail = trip_with_itinerary(
        accessible_trips_for_user(request.user)
    ).get(id=trip.id)

    return Response({
        "proposal": _proposal_data(proposal, request.user),
        "trip": TripDetailSerializer(detail).data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def proposal_discard(request, trip_id, proposal_id):
    trip = get_accessible_trip(request.user, trip_id)
    proposal = _get_proposal(trip, proposal_id)

    # Integrantes só descartam as propostas que elas mesmas pediram.
    if trip_role(request.user, trip) != "owner" and (
        proposal.created_by_id != request.user.id
    ):
        raise NotFound()

    proposal = discard_proposal(proposal, request.user)
    return Response(_proposal_data(proposal, request.user))


# ---------------------------------------------------------------------------
# Dias
# ---------------------------------------------------------------------------


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def day_detail(request, trip_id, day_id):
    day = get_user_day(request.user, trip_id, day_id)

    serializer = TripDayUpdateSerializer(day, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(TripDaySerializer(day).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def day_reorder(request, trip_id, day_id):
    day = get_user_day(request.user, trip_id, day_id)

    serializer = ReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    sent_ids = serializer.validated_data["activity_ids"]

    activities = {activity.id: activity for activity in day.activities.all()}

    if len(sent_ids) != len(set(sent_ids)) or set(sent_ids) != set(activities):
        raise ValidationError({
            "activity_ids": [
                "Envie todas as atividades deste dia, sem repetir."
            ],
        })

    with transaction.atomic():
        for position, activity_id in enumerate(sent_ids, start=1):
            activity = activities[activity_id]
            activity.order = position
            activity.save(update_fields=["order", "updated_at"])

    return Response(TripDaySerializer(day).data)


# ---------------------------------------------------------------------------
# Atividades
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activity_list(request, trip_id):
    trip = get_user_trip(request.user, trip_id)

    serializer = ActivitySerializer(data=request.data, context={"trip": trip})
    serializer.is_valid(raise_exception=True)

    day = serializer.validated_data["day"]
    order = serializer.validated_data.get("order") or next_activity_order(day)
    activity = serializer.save(order=order)

    return Response(
        ActivitySerializer(activity).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def activity_detail(request, trip_id, activity_id):
    activity = get_user_activity(request.user, trip_id, activity_id)

    if request.method == "DELETE":
        activity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    trip = activity.day.trip
    serializer = ActivitySerializer(
        activity,
        data=request.data,
        partial=True,
        context={"trip": trip},
    )
    serializer.is_valid(raise_exception=True)

    new_day = serializer.validated_data.get("day")
    moved = new_day is not None and new_day.id != activity.day_id

    if moved and "order" not in serializer.validated_data:
        # Atividade movida para outro dia vai para o final dele.
        activity = serializer.save(order=next_activity_order(new_day))
    else:
        activity = serializer.save()

    return Response(ActivitySerializer(activity).data)
