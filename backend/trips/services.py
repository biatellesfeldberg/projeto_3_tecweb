"""Regras de negócio das viagens usadas pelas views."""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Max, Prefetch

from .models import Activity, Trip, TripDay


def trip_with_itinerary(queryset):
    """Carrega dias e atividades de uma vez, evitando várias consultas."""
    return queryset.prefetch_related(
        Prefetch(
            "days",
            queryset=TripDay.objects.order_by("date").prefetch_related(
                Prefetch(
                    "activities",
                    queryset=Activity.objects.select_related("day__trip"),
                )
            ),
        )
    )


def apply_profile_preferences(user, data):
    """
    Preenche estilo, ritmo e interesses com os do perfil quando eles não
    foram enviados na criação da viagem.
    """
    for field in ("style", "pace"):
        if field not in data:
            data[field] = getattr(user, field, "") or ""

    if "interests" not in data:
        data["interests"] = list(getattr(user, "interests", []) or [])

    return data


@transaction.atomic
def sync_days(trip):
    """
    Garante um dia para cada data da viagem.

    Datas novas ganham dias vazios. Dias fora do período são apagados junto
    com suas atividades. No fim, os dias são renumerados a partir de 1.
    """
    dates = [
        trip.start_date + timedelta(days=offset)
        for offset in range(trip.duration_days)
    ]

    trip.days.exclude(date__in=dates).delete()

    # Afasta os números atuais para não colidir com a regra de número único
    # por viagem durante a renumeração.
    trip.days.update(day_number=F("day_number") + 10000)

    existing = {day.date: day for day in trip.days.all()}

    for number, date in enumerate(dates, start=1):
        day = existing.get(date)
        if day is None:
            TripDay.objects.create(trip=trip, date=date, day_number=number)
        else:
            day.day_number = number
            day.save(update_fields=["day_number", "updated_at"])


def next_activity_order(day):
    current = day.activities.aggregate(highest=Max("order"))["highest"]
    return (current or 0) + 1


@transaction.atomic
def duplicate_trip(trip):
    """Cria uma cópia da viagem, com os mesmos dias e atividades."""
    copy_fields = [
        "description",
        "origin",
        "destination",
        "start_date",
        "end_date",
        "travelers_count",
        "budget",
        "currency",
        "mode",
        "style",
        "pace",
        "transport",
        "interests",
        "cover_image_url",
        "ai_summary",
        "lodging_suggestions",
        "cost_estimate",
        "itinerary_generated_at",
    ]

    suffix = " (cópia)"
    max_length = Trip._meta.get_field("title").max_length

    new_trip = Trip.objects.create(
        owner=trip.owner,
        title=trip.title[: max_length - len(suffix)] + suffix,
        status=Trip.Status.PLANNING,
        **{field: getattr(trip, field) for field in copy_fields},
    )

    activity_fields = [
        field.name
        for field in Activity._meta.concrete_fields
        if field.name not in {"id", "day", "created_at", "updated_at"}
    ]

    for day in trip.days.order_by("date"):
        new_day = TripDay.objects.create(
            trip=new_trip,
            date=day.date,
            day_number=day.day_number,
            title=day.title,
            notes=day.notes,
        )
        Activity.objects.bulk_create([
            Activity(
                day=new_day,
                **{field: getattr(activity, field) for field in activity_fields},
            )
            for activity in day.activities.all()
        ])

    return new_trip
