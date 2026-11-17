from django.contrib.auth import get_user_model
from django.db.models import Q

from rest_framework.exceptions import NotFound

from .models import Activity, Trip, TripDay

User = get_user_model()


def trips_for_user(user):
    """Viagens que a pessoa pode gerenciar: somente as próprias."""
    if not getattr(user, "is_authenticated", False):
        return Trip.objects.none()

    return Trip.objects.filter(owner=user)


def accessible_trips_for_user(user):
    """Viagens próprias ou com participação aceita."""
    if not getattr(user, "is_authenticated", False):
        return Trip.objects.none()

    return Trip.objects.filter(
        Q(owner=user)
        | Q(
            memberships__user=user,
            memberships__status="accepted",
        )
    ).distinct()


def trip_role(user, trip):
    """Retorna owner, participant ou None, conforme a viagem."""
    if not getattr(user, "is_authenticated", False):
        return None

    if trip.owner_id == user.pk:
        return "owner"

    if trip.memberships.filter(
        user=user,
        status="accepted",
    ).exists():
        return "participant"

    return None


def can_view_trip(user, trip):
    return trip_role(user, trip) is not None


def can_manage_trip(user, trip):
    return trip_role(user, trip) == "owner"


def trip_participants(trip):
    """Organizadora e integrantes aceitas, sem usar travelers_count."""
    return User.objects.filter(
        Q(pk=trip.owner_id)
        | Q(
            trip_memberships__trip=trip,
            trip_memberships__status="accepted",
        )
    ).distinct()


def _get_or_404(queryset, **lookup):
    obj = queryset.filter(**lookup).first()

    if obj is None:
        raise NotFound()

    return obj


def get_accessible_trip(user, trip_id):
    """
    Use antes de consultar recursos compartilhados
    ou gravar o próprio voto/resposta.
    """
    return _get_or_404(
        accessible_trips_for_user(user),
        id=trip_id,
    )


def get_manageable_trip(user, trip_id):
    """Use antes de alterar recursos administrados pela organizadora."""
    return _get_or_404(
        trips_for_user(user),
        id=trip_id,
    )


def get_user_trip(user, trip_id):
    """Nome anterior mantido para os endpoints e imports existentes."""
    return get_manageable_trip(user, trip_id)


def get_user_day(user, trip_id, day_id):
    trip = get_manageable_trip(user, trip_id)

    return _get_or_404(
        TripDay.objects.filter(trip=trip),
        id=day_id,
    )


def get_user_activity(user, trip_id, activity_id):
    trip = get_manageable_trip(user, trip_id)

    return _get_or_404(
        Activity.objects.filter(day__trip=trip),
        id=activity_id,
    )