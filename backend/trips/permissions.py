from rest_framework.exceptions import NotFound

from .models import Activity, Trip, TripDay


def trips_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return Trip.objects.none()

    return Trip.objects.filter(owner=user)


def _get_or_404(queryset, **lookup):
    obj = queryset.filter(**lookup).first()

    if obj is None:
        raise NotFound()

    return obj


def get_user_trip(user, trip_id):
    return _get_or_404(
        trips_for_user(user),
        id=trip_id,
    )


def get_user_day(user, trip_id, day_id):
    trip = get_user_trip(user, trip_id)

    return _get_or_404(
        TripDay.objects.filter(trip=trip),
        id=day_id,
    )


def get_user_activity(user, trip_id, activity_id):
    trip = get_user_trip(user, trip_id)

    return _get_or_404(
        Activity.objects.filter(day__trip=trip),
        id=activity_id,
    )