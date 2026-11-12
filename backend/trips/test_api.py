from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Activity, Trip, TripDay
from .services import sync_days


User = get_user_model()


def make_user(email, **fields):
    return User.objects.create_user(
        username=email,
        email=email,
        password="senha-forte-123",
        first_name=email.split("@")[0].title(),
        **fields,
    )


def make_trip(owner, **fields):
    data = {
        "title": "Lisboa com calma",
        "origin": "São Paulo, Brasil",
        "destination": "Lisboa, Portugal",
        "start_date": date(2027, 5, 12),
        "end_date": date(2027, 5, 14),
        "travelers_count": 4,
    }
    data.update(fields)
    trip = Trip.objects.create(owner=owner, **data)
    sync_days(trip)
    return trip


class TripApiTestCase(APITestCase):
    def setUp(self):
        self.bia = make_user(
            "bia@exemplo.com",
            style="intermediate",
            pace="relaxed",
            interests=["culture", "gastronomy"],
        )
        self.ana = make_user("ana@exemplo.com")
        self.login(self.bia)

    def login(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class TripCrudTests(TripApiTestCase):
    def test_create_trip_creates_days_and_uses_profile_preferences(self):
        response = self.client.post(
            "/api/trips/",
            {
                "title": "Lisboa com calma",
                "origin": "São Paulo, Brasil",
                "destination": "Lisboa, Portugal",
                "start_date": "2027-05-12",
                "end_date": "2027-05-18",
                "travelers_count": 4,
                "budget": "32000.00",
                "mode": "group",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["duration_days"], 7)
        self.assertEqual(len(data["days"]), 7)
        self.assertEqual(data["days"][0]["date"], "2027-05-12")
        self.assertEqual(data["days"][6]["day_number"], 7)
        self.assertEqual(data["budget"], "32000.00")
        self.assertEqual(data["status"], "planning")
        # Preferências vieram do perfil.
        self.assertEqual(data["style"], "intermediate")
        self.assertEqual(data["pace"], "relaxed")
        self.assertEqual(data["interests"], ["culture", "gastronomy"])
        self.assertEqual(Trip.objects.get().owner, self.bia)

    def test_sent_preferences_win_over_profile(self):
        response = self.client.post(
            "/api/trips/",
            {
                "title": "Praia",
                "origin": "São Paulo",
                "start_date": "2027-01-10",
                "end_date": "2027-01-10",
                "style": "economic",
                "interests": ["beach", "beach"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["style"], "economic")
        self.assertEqual(response.data["interests"], ["beach"])
        self.assertEqual(response.data["destination"], "")

    def test_owner_sent_in_body_is_ignored(self):
        response = self.client.post(
            "/api/trips/",
            {
                "title": "Teste",
                "origin": "SP",
                "start_date": "2027-01-10",
                "end_date": "2027-01-11",
                "owner": self.ana.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Trip.objects.get().owner, self.bia)

    def test_create_validates_dates_and_choices(self):
        base = {"title": "X", "origin": "SP"}

        response = self.client.post(
            "/api/trips/",
            {**base, "start_date": "2027-05-18", "end_date": "2027-05-12"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

        response = self.client.post(
            "/api/trips/",
            {**base, "start_date": "2027-01-01", "end_date": "2027-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

        response = self.client.post(
            "/api/trips/",
            {
                **base,
                "start_date": "2027-01-01",
                "end_date": "2027-01-02",
                "interests": ["praia"],
                "status": "cancelada",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("interests", response.data)
        self.assertIn("status", response.data)
        self.assertFalse(Trip.objects.exists())

    def test_list_returns_summaries_and_filters_by_status(self):
        make_trip(self.bia, title="Planejando")
        make_trip(self.bia, title="Feita", status=Trip.Status.COMPLETED)

        response = self.client.get("/api/trips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertNotIn("days", response.data[0])

        response = self.client.get("/api/trips/?status=completed")
        self.assertEqual([t["title"] for t in response.data], ["Feita"])

        response = self.client.get("/api/trips/?status=qualquer")
        self.assertEqual(response.status_code, 400)

    def test_empty_list(self):
        response = self.client.get("/api/trips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_detail_returns_days_and_activities_in_order(self):
        trip = make_trip(self.bia)
        day = trip.days.get(day_number=1)
        Activity.objects.create(day=day, title="Segunda", order=2)
        Activity.objects.create(
            day=day,
            title="Primeira",
            order=1,
            estimated_cost=Decimal("60.00"),
        )

        response = self.client.get(f"/api/trips/{trip.id}/")

        self.assertEqual(response.status_code, 200)
        activities = response.data["days"][0]["activities"]
        self.assertEqual([a["title"] for a in activities], ["Primeira", "Segunda"])
        self.assertEqual(activities[0]["total_cost"], "240.00")

    def test_update_status(self):
        trip = make_trip(self.bia)

        response = self.client.patch(
            f"/api/trips/{trip.id}/", {"status": "upcoming"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "upcoming")

    def test_changing_dates_adjusts_days(self):
        trip = make_trip(self.bia)  # 12 a 14 de maio
        last_day = trip.days.get(date=date(2027, 5, 14))
        Activity.objects.create(day=last_day, title="Vai sumir")
        first_day = trip.days.get(date=date(2027, 5, 12))
        Activity.objects.create(day=first_day, title="Fica")

        response = self.client.patch(
            f"/api/trips/{trip.id}/",
            {"start_date": "2027-05-11", "end_date": "2027-05-13"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        days = response.data["days"]
        self.assertEqual(
            [(d["date"], d["day_number"]) for d in days],
            [("2027-05-11", 1), ("2027-05-12", 2), ("2027-05-13", 3)],
        )
        self.assertEqual(days[1]["activities"][0]["title"], "Fica")
        self.assertFalse(Activity.objects.filter(title="Vai sumir").exists())

    def test_patch_validates_dates_against_saved_values(self):
        trip = make_trip(self.bia)

        response = self.client.patch(
            f"/api/trips/{trip.id}/", {"end_date": "2027-05-01"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        trip.refresh_from_db()
        self.assertEqual(trip.end_date, date(2027, 5, 14))

    def test_delete_trip(self):
        trip = make_trip(self.bia)

        response = self.client.delete(f"/api/trips/{trip.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Trip.objects.exists())
        self.assertFalse(TripDay.objects.exists())

    def test_duplicate_trip_copies_days_and_activities(self):
        trip = make_trip(self.bia, status=Trip.Status.COMPLETED)
        day = trip.days.get(day_number=1)
        day.notes = "Levar casaco"
        day.save()
        Activity.objects.create(day=day, title="Café", start_time=time(9, 0))

        response = self.client.post(f"/api/trips/{trip.id}/duplicate/")

        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertNotEqual(data["id"], trip.id)
        self.assertEqual(data["title"], "Lisboa com calma (cópia)")
        self.assertEqual(data["status"], "planning")
        self.assertEqual(len(data["days"]), 3)
        self.assertEqual(data["days"][0]["notes"], "Levar casaco")
        self.assertEqual(data["days"][0]["activities"][0]["title"], "Café")
        # A original não muda.
        self.assertEqual(Activity.objects.filter(day__trip=trip).count(), 1)
        self.assertEqual(Trip.objects.count(), 2)


class DayAndActivityTests(TripApiTestCase):
    def setUp(self):
        super().setUp()
        self.trip = make_trip(self.bia)
        self.day1 = self.trip.days.get(day_number=1)
        self.day2 = self.trip.days.get(day_number=2)
        self.base = f"/api/trips/{self.trip.id}"

    def test_update_day_notes(self):
        response = self.client.patch(
            f"{self.base}/days/{self.day1.id}/",
            {"notes": "Levar casaco.", "date": "2030-01-01"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notes"], "Levar casaco.")
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.date, date(2027, 5, 12))

    def test_create_activity_goes_to_end_of_day(self):
        Activity.objects.create(day=self.day1, title="Já existia", order=1)

        response = self.client.post(
            f"{self.base}/activities/",
            {
                "day": self.day1.id,
                "title": "Miradouro",
                "category": "sightseeing",
                "start_time": "15:00",
                "estimated_cost": "10.00",
                "cost_type": "per_person",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["order"], 2)
        self.assertEqual(response.data["start_time"], "15:00:00")
        self.assertEqual(response.data["total_cost"], "40.00")

    def test_create_activity_validates_times_and_day(self):
        response = self.client.post(
            f"{self.base}/activities/",
            {
                "day": self.day1.id,
                "title": "X",
                "start_time": "15:00",
                "end_time": "14:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_time", response.data)

        response = self.client.post(
            f"{self.base}/activities/", {"title": "Sem dia"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("day", response.data)

    def test_update_and_move_activity(self):
        activity = Activity.objects.create(day=self.day1, title="Café", order=1)
        Activity.objects.create(day=self.day2, title="Outra", order=1)

        response = self.client.patch(
            f"{self.base}/activities/{activity.id}/",
            {"title": "Café da manhã", "day": self.day2.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Café da manhã")
        self.assertEqual(response.data["day"], self.day2.id)
        self.assertEqual(response.data["order"], 2)

    def test_patch_end_time_is_checked_against_saved_start_time(self):
        activity = Activity.objects.create(
            day=self.day1, title="Café", start_time=time(9, 0)
        )

        response = self.client.patch(
            f"{self.base}/activities/{activity.id}/",
            {"end_time": "08:00"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_delete_activity(self):
        activity = Activity.objects.create(day=self.day1, title="Café")

        response = self.client.delete(f"{self.base}/activities/{activity.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Activity.objects.exists())

    def test_reorder_activities(self):
        a = Activity.objects.create(day=self.day1, title="A", order=1)
        b = Activity.objects.create(day=self.day1, title="B", order=2)
        c = Activity.objects.create(day=self.day1, title="C", order=3)

        response = self.client.post(
            f"{self.base}/days/{self.day1.id}/reorder/",
            {"activity_ids": [c.id, a.id, b.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [x["title"] for x in response.data["activities"]], ["C", "A", "B"]
        )

    def test_reorder_requires_exactly_the_day_activities(self):
        a = Activity.objects.create(day=self.day1, title="A", order=1)
        b = Activity.objects.create(day=self.day1, title="B", order=2)
        other = Activity.objects.create(day=self.day2, title="Outro dia")

        for ids in ([a.id], [a.id, a.id, b.id], [a.id, b.id, other.id]):
            response = self.client.post(
                f"{self.base}/days/{self.day1.id}/reorder/",
                {"activity_ids": ids},
                format="json",
            )
            self.assertEqual(response.status_code, 400, ids)


class TripPrivacyTests(TripApiTestCase):
    """Uma pessoa nunca acessa nem altera viagens de outra (sempre 404)."""

    def setUp(self):
        super().setUp()
        self.ana_trip = make_trip(self.ana, title="Viagem da Ana")
        self.ana_day = self.ana_trip.days.get(day_number=1)
        self.ana_activity = Activity.objects.create(
            day=self.ana_day, title="Atividade da Ana"
        )
        self.bia_trip = make_trip(self.bia)
        self.bia_day = self.bia_trip.days.get(day_number=1)

    def test_list_only_shows_own_trips(self):
        response = self.client.get("/api/trips/")
        self.assertEqual([t["id"] for t in response.data], [self.bia_trip.id])

    def test_cannot_read_edit_delete_or_duplicate_other_trip(self):
        url = f"/api/trips/{self.ana_trip.id}/"

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.patch(url, {"title": "Hack"}, format="json").status_code,
            404,
        )
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.client.post(f"{url}duplicate/").status_code, 404)

        self.ana_trip.refresh_from_db()
        self.assertEqual(self.ana_trip.title, "Viagem da Ana")
        self.assertEqual(Trip.objects.filter(owner=self.bia).count(), 1)

    def test_cannot_touch_days_or_activities_of_other_trip(self):
        base = f"/api/trips/{self.ana_trip.id}"

        responses = [
            self.client.patch(
                f"{base}/days/{self.ana_day.id}/", {"notes": "x"}, format="json"
            ),
            self.client.post(
                f"{base}/days/{self.ana_day.id}/reorder/",
                {"activity_ids": [self.ana_activity.id]},
                format="json",
            ),
            self.client.post(
                f"{base}/activities/",
                {"day": self.ana_day.id, "title": "x"},
                format="json",
            ),
            self.client.patch(
                f"{base}/activities/{self.ana_activity.id}/",
                {"title": "x"},
                format="json",
            ),
            self.client.delete(f"{base}/activities/{self.ana_activity.id}/"),
        ]

        self.assertEqual([r.status_code for r in responses], [404] * 5)
        self.ana_activity.refresh_from_db()
        self.assertEqual(self.ana_activity.title, "Atividade da Ana")

    def test_other_ids_through_own_trip_url_are_not_found(self):
        base = f"/api/trips/{self.bia_trip.id}"

        response = self.client.patch(
            f"{base}/activities/{self.ana_activity.id}/",
            {"title": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.patch(
            f"{base}/days/{self.ana_day.id}/", {"notes": "x"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_create_or_move_activity_into_other_trip_day(self):
        base = f"/api/trips/{self.bia_trip.id}"

        response = self.client.post(
            f"{base}/activities/",
            {"day": self.ana_day.id, "title": "Intrusa"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["day"], ["Este dia não pertence a esta viagem."]
        )

        own = Activity.objects.create(day=self.bia_day, title="Minha")
        response = self.client.patch(
            f"{base}/activities/{own.id}/",
            {"day": self.ana_day.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.ana_day.activities.filter(title="Minha").exists())

    def test_routes_require_token(self):
        self.client.credentials()
        base = f"/api/trips/{self.bia_trip.id}"

        responses = [
            self.client.get("/api/trips/"),
            self.client.post("/api/trips/", {}, format="json"),
            self.client.get(f"{base}/"),
            self.client.post(f"{base}/duplicate/"),
            self.client.post(f"{base}/activities/", {}, format="json"),
        ]

        self.assertEqual([r.status_code for r in responses], [401] * 5)
