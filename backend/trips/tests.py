from django.test import TestCase

from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import Activity, Trip, TripDay


User = get_user_model()


class TripModelsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bia", password="senha-forte-123")
        self.trip = Trip.objects.create(
            owner=self.user,
            title="Lisboa com calma",
            origin="São Paulo, Brasil",
            destination="Lisboa, Portugal",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 18),
            travelers_count=4,
            budget=Decimal("32000.00"),
            style=Trip.Style.INTERMEDIATE,
            pace=Trip.Pace.RELAXED,
            transport=Trip.Transport.PLANE,
            interests=["gastronomia", "cultura"],
        )
        self.day = TripDay.objects.create(
            trip=self.trip, date=date(2027, 5, 12), day_number=1
        )

    def test_trip_defaults_and_duration(self):
        self.assertEqual(self.trip.status, Trip.Status.PLANNING)
        self.assertEqual(self.trip.mode, Trip.Mode.SOLO)
        self.assertEqual(self.trip.duration_days, 7)
        self.assertEqual(self.user.trips.count(), 1)

    def test_trip_end_date_before_start_date_is_invalid(self):
        self.trip.end_date = date(2027, 5, 1)
        with self.assertRaises(ValidationError):
            self.trip.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.trip.save()

    def test_trip_destination_can_be_empty(self):
        trip = Trip(
            owner=self.user,
            title="Férias em grupo",
            origin="São Paulo, Brasil",
            start_date=date(2027, 7, 1),
            end_date=date(2027, 7, 5),
            mode=Trip.Mode.GROUP,
        )
        trip.full_clean()  # não deve levantar erro

    def test_day_must_be_inside_trip_period(self):
        day = TripDay(trip=self.trip, date=date(2027, 6, 1), day_number=2)
        with self.assertRaises(ValidationError):
            day.full_clean()

    def test_day_date_is_unique_per_trip(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TripDay.objects.create(trip=self.trip, date=date(2027, 5, 12), day_number=2)

    def test_activities_are_ordered_and_cost_is_calculated(self):
        second = Activity.objects.create(
            day=self.day,
            title="Descobrir Alfama a pé",
            category=Activity.Category.CULTURE,
            start_time=time(11, 0),
            duration_minutes=120,
            order=2,
        )
        first = Activity.objects.create(
            day=self.day,
            title="Café e uma volta pela Baixa",
            category=Activity.Category.GASTRONOMY,
            start_time=time(9, 0),
            duration_minutes=90,
            location_name="Baixa",
            latitude=Decimal("38.711000"),
            longitude=Decimal("-9.137000"),
            estimated_cost=Decimal("60.00"),
            order=1,
        )
        self.assertEqual(list(self.day.activities.all()), [first, second])
        self.assertEqual(first.total_cost, Decimal("240.00"))  # 60 x 4 viajantes

    def test_activity_end_time_before_start_time_is_invalid(self):
        activity = Activity(
            day=self.day,
            title="Miradouro",
            start_time=time(15, 0),
            end_time=time(14, 0),
        )
        with self.assertRaises(ValidationError):
            activity.full_clean()

    def test_deleting_trip_deletes_days_and_activities(self):
        Activity.objects.create(day=self.day, title="Miradouro e tempo livre")
        self.trip.delete()
        self.assertEqual(TripDay.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)
