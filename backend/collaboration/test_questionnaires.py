from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from trips.models import Trip
from .models import Friendship, TripMembership, TripQuestionnaire


User = get_user_model()


class QuestionnaireTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Roteiro!2026Teste",
            first_name="Bia",
            interests=["beach"],
        )

        cls.b = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="Roteiro!2026Teste",
            first_name="Ana",
        )

        cls.c = User.objects.create_user(
            username="luana",
            email="luana@example.com",
            password="Roteiro!2026Teste",
            first_name="Luana",
        )

        cls.d = User.objects.create_user(
            username="renata",
            email="renata@example.com",
            password="Roteiro!2026Teste",
            first_name="Renata",
        )

        for user in [cls.a, cls.b, cls.c, cls.d]:
            Token.objects.create(user=user)

        cls.trip = Trip.objects.create(
            owner=cls.a,
            title="Viagem do grupo",
            origin="São Paulo",
            mode="group",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 14),
            travelers_count=9,
        )

        Friendship.objects.create(
            sender=cls.a,
            recipient=cls.b,
            status="accepted",
        )

        TripMembership.objects.create(
            trip=cls.trip,
            user=cls.b,
            invited_by=cls.a,
            status="accepted",
        )

        TripMembership.objects.create(
            trip=cls.trip,
            user=cls.c,
            invited_by=cls.a,
            status="pending",
        )

    def setUp(self):
        self.auth(self.a)

        self.url = (
            f"/api/trips/{self.trip.pk}/questionnaire/me/"
        )

        self.progress_url = (
            f"/api/trips/{self.trip.pk}/questionnaire/progress/"
        )

    def auth(self, user):
        token = Token.objects.get(user=user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

    def payload(self):
        return {
            "landscape": "city",
            "max_budget": "8000.00",
            "days": 7,
            "pace": "relaxed",
            "gastronomy_importance": 5,
            "destination_preference": "international",
            "climate": "mild",
            "accommodation": "hotel",
            "interests": ["culture", "gastronomy"],
            "avoided_destinations": ["Destino a evitar"],
            "notes": "Prefiro dias leves.",
        }

    def save_answer(self, user=None):
        self.auth(user or self.a)

        return self.client.put(
            self.url,
            self.payload(),
            format="json",
        )

    def test_unanswered_profile(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"answered": False, "answers": None},
        )

    def test_owner_can_answer(self):
        response = self.save_answer()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["answered"])

        answers = response.data["answers"]

        self.assertEqual(answers["user"], self.a.pk)
        self.assertEqual(answers["currency"], "BRL")
        self.assertEqual(answers["max_budget"], "8000.00")

    def test_accepted_member_can_answer(self):
        response = self.save_answer(self.b)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["answers"]["user"],
            self.b.pk,
        )

    def test_put_replaces_without_duplicates(self):
        self.save_answer()

        data = self.payload()
        data.pop("notes")
        data["avoided_destinations"] = [
            "Lisboa",
            "Lisboa",
            "Paris",
        ]
        data["interests"] = ["culture", "culture"]

        response = self.client.put(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TripQuestionnaire.objects.count(), 1)

        answers = response.data["answers"]

        self.assertEqual(answers["notes"], "")
        self.assertEqual(answers["interests"], ["culture"])
        self.assertEqual(
            answers["avoided_destinations"],
            ["Lisboa", "Paris"],
        )

    def test_patch_preserves_other_fields_and_currency(self):
        self.save_answer()

        self.trip.currency = "USD"
        self.trip.save()

        response = self.client.patch(
            self.url,
            {"days": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        answers = response.data["answers"]

        self.assertEqual(answers["days"], 5)
        self.assertEqual(answers["max_budget"], "8000.00")
        self.assertEqual(answers["currency"], "BRL")
        self.assertEqual(
            answers["notes"],
            "Prefiro dias leves.",
        )

    def test_patch_requires_previous_full_answer(self):
        response = self.client.patch(
            self.url,
            {"days": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(TripQuestionnaire.objects.exists())

    def test_put_requires_complete_answer(self):
        response = self.client.put(
            self.url,
            {"days": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TripQuestionnaire.objects.exists())

    def test_invalid_answers_are_rejected(self):
        cases = [
            ("landscape", "invalid"),
            ("max_budget", "0"),
            ("max_budget", "-1"),
            ("days", 0),
            ("days", 61),
            ("pace", "invalid"),
            ("gastronomy_importance", 0),
            ("gastronomy_importance", 6),
            ("destination_preference", "invalid"),
            ("climate", "invalid"),
            ("accommodation", "invalid"),
            ("interests", []),
            ("interests", ["invalid"]),
            ("avoided_destinations", "Lisboa"),
            ("notes", "x" * 501),
        ]

        for field, value in cases:
            with self.subTest(field=field, value=value):
                data = self.payload()
                data[field] = value

                response = self.client.put(
                    self.url,
                    data,
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

        self.assertFalse(TripQuestionnaire.objects.exists())

    def test_cannot_forge_identity_or_currency(self):
        self.save_answer()

        cases = [
            ("user", self.b.pk),
            ("trip", self.trip.pk),
            ("currency", "USD"),
            ("id", 99),
        ]

        for field, value in cases:
            with self.subTest(field=field):
                response = self.client.patch(
                    self.url,
                    {field: value},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

        self.assertEqual(
            TripQuestionnaire.objects.get().user_id,
            self.a.pk,
        )

    def test_progress_counts_owner_and_accepted_members_only(self):
        response = self.client.get(self.progress_url)

        self.assertEqual(response.data["total_members"], 2)
        self.assertEqual(response.data["answered_count"], 0)
        self.assertFalse(response.data["all_answered"])

        self.save_answer(self.a)

        response = self.client.get(self.progress_url)
        self.assertEqual(response.data["answered_count"], 1)

        self.save_answer(self.b)

        response = self.client.get(self.progress_url)

        self.assertEqual(response.data["answered_count"], 2)
        self.assertEqual(response.data["remaining_count"], 0)
        self.assertTrue(response.data["all_answered"])
        self.assertNotIn("max_budget", repr(response.data))

    def test_pending_invitee_is_blocked(self):
        self.auth(self.c)

        self.assertEqual(
            self.client.get(self.url).status_code,
            404,
        )

        self.assertEqual(
            self.client.put(
                self.url,
                self.payload(),
                format="json",
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.get(self.progress_url).status_code,
            404,
        )

    def test_outsider_is_blocked(self):
        self.auth(self.d)

        self.assertEqual(
            self.client.get(self.url).status_code,
            404,
        )

        self.assertEqual(
            self.client.put(
                self.url,
                self.payload(),
                format="json",
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.get(self.progress_url).status_code,
            404,
        )

    def test_authentication_is_required(self):
        self.client.credentials()

        cases = [
            ("get", self.url),
            ("put", self.url),
            ("patch", self.url),
            ("get", self.progress_url),
        ]

        for method, url in cases:
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 401)

    def test_cannot_read_someone_elses_answers(self):
        self.save_answer(self.b)
        self.auth(self.a)

        response = self.client.get(
            self.url + f"?user_id={self.b.pk}"
        )

        self.assertEqual(
            response.data,
            {"answered": False, "answers": None},
        )

    def test_leave_deletes_answer(self):
        self.save_answer(self.b)

        response = self.client.post(
            f"/api/trips/{self.trip.pk}/leave/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            TripQuestionnaire.objects.filter(
                user=self.b,
            ).exists()
        )

        self.assertEqual(
            self.client.get(self.url).status_code,
            404,
        )

        self.auth(self.a)

        self.assertEqual(
            self.client.get(
                self.progress_url
            ).data["total_members"],
            1,
        )

    def test_removal_deletes_answer(self):
        self.save_answer(self.b)
        self.auth(self.a)

        response = self.client.delete(
            f"/api/trips/{self.trip.pk}/members/{self.b.pk}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            TripQuestionnaire.objects.filter(
                user=self.b,
            ).exists()
        )

    def test_rejoining_starts_unanswered(self):
        self.save_answer(self.b)

        self.client.post(
            f"/api/trips/{self.trip.pk}/leave/"
        )

        self.auth(self.a)

        response = self.client.post(
            f"/api/trips/{self.trip.pk}/members/",
            {"user_id": self.b.pk},
            format="json",
        )

        invitation_id = response.data["id"]

        self.auth(self.b)

        self.client.post(
            f"/api/trip-invitations/{invitation_id}/accept/"
        )

        self.assertEqual(
            self.client.get(self.url).data,
            {"answered": False, "answers": None},
        )

    def test_new_member_changes_progress(self):
        self.save_answer(self.a)
        self.save_answer(self.b)

        self.assertTrue(
            self.client.get(
                self.progress_url
            ).data["all_answered"]
        )

        invitation = TripMembership.objects.get(
            user=self.c,
            trip=self.trip,
        )

        self.auth(self.c)

        self.client.post(
            f"/api/trip-invitations/{invitation.pk}/accept/"
        )

        progress = self.client.get(self.progress_url).data

        self.assertEqual(progress["total_members"], 3)
        self.assertEqual(progress["answered_count"], 2)
        self.assertFalse(progress["all_answered"])

    def test_global_profile_is_not_changed(self):
        self.save_answer()
        self.a.refresh_from_db()

        self.assertEqual(self.a.interests, ["beach"])
        self.assertEqual(self.a.style, "")

    def test_database_prevents_duplicate_answer(self):
        self.save_answer()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TripQuestionnaire.objects.create(
                    trip=self.trip,
                    user=self.a,
                    **self.payload(),
                )