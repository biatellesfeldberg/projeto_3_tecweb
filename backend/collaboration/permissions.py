from rest_framework.exceptions import NotFound

from .models import TripMembership, TripPoll


def pending_trip_invitations_for_user(user):
    """Convites pendentes recebidos pela própria pessoa."""
    if not getattr(user, "is_authenticated", False):
        return TripMembership.objects.none()

    return TripMembership.objects.filter(
        user=user,
        status=TripMembership.Status.PENDING,
    )


def get_poll_for_trip(trip, poll_id, *, for_update=False):
    """
    Recebe uma viagem JÁ autorizada por get_accessible_trip
    ou get_manageable_trip.

    O filtro por viagem impede acessar uma votação usando
    o ID de outra viagem.

    for_update=True deve ser usado dentro de transaction.atomic().
    """
    polls = TripPoll.objects.all()

    if for_update:
        polls = polls.select_for_update()

    poll = polls.filter(
        pk=poll_id,
        trip=trip,
    ).first()

    if poll is None:
        raise NotFound()

    return poll