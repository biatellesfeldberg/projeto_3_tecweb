from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from core.gemini import GeminiUnavailableError
from trips.models import Trip

from .models import (
    GroupDestinationRecommendation,
    TripMembership,
    TripQuestionnaire,
)


class GroupDestinationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        (
            cls.owner,
            cls.member,
            cls.pending,
            cls.outsider,
        ) = [
            User.objects.create_user(
                username=name,
                email=f"{name}@example.com",
            )
            for name in (
                "owner",
                "member",
                "pending",
                "outsider",
            )
        ]

        cls.trip = Trip.objects.create(
            owner=cls.owner,
            title="Grupo",
            origin="São Paulo",
            mode="group",
            start_date=date(2027, 5, 1),
            end_date=date(2027, 5, 4),
            currency="BRL",
            travelers_count=50,
        )

        for user, status in (
            (cls.member, "accepted"),
            (cls.pending, "pending"),
        ):
            TripMembership.objects.create(
                trip=cls.trip,
                user=user,
                invited_by=cls.owner,
                status=status,
            )

        for user in (
            cls.owner,
            cls.member,
            cls.pending,
        ):
            TripQuestionnaire.objects.create(
                trip=cls.trip,
                user=user,
                currency="BRL",
                landscape="city",
                max_budget="5000.00",
                days=4,
                pace="moderate",
                gastronomy_importance=5,
                destination_preference="domestic",
                climate="mild",
                accommodation="hotel",
                interests=[
                    "culture",
                    "gastronomy",
                ],
                avoided_destinations=[],
                notes="Nota privada",
            )

    def setUp(self):
        self.client.force_authenticate(self.owner)

        self.url = (
            f"/api/trips/{self.trip.pk}/"
            "group-destinations/"
        )

        self.payload = {
            "origin_country_code": "BR",
        }

        base = {
            "country": "Brasil",
            "country_code": "BR",
            "currency": "BRL",
            "cost_min": 2000,
            "cost_max": 3000,
            "landscape": "city",
            "climate": "mild",
            "pace": "moderate",
            "accommodation": "hotel",
            "interests": [
                "culture",
                "gastronomy",
            ],
            "reason": (
                "Cultura e gastronomia "
                "com ritmo moderado."
            ),
            "caveat": (
                "Custos estimados, "
                "sujeitos a confirmação."
            ),
        }

        self.raw = {
            "destinations": [
                {
                    **deepcopy(base),
                    "city": city,
                }
                for city in (
                    "Curitiba",
                    "São Paulo",
                    "Belo Horizonte",
                )
            ],
        }

        self.mock = patch(
            "collaboration.destinations.generate_json",
            return_value=self.raw,
        ).start()

        self.addCleanup(patch.stopall)

    def post(self, **extra):
        return self.client.post(
            self.url,
            {
                **self.payload,
                **extra,
            },
            format="json",
        )

    def test_score_costs_alternatives_and_cached_read(self):
        response = self.post()

        self.assertEqual(
            response.status_code,
            200,
            response.data,
        )

        data = response.data["result"]

        self.assertEqual(
            data["participants_count"],
            2,
        )

        self.assertEqual(
            data["duration_days"],
            4,
        )

        self.assertEqual(
            len(data["alternatives"]),
            2,
        )

        self.assertEqual(
            data["recommendation"]["compatibility"]["score"],
            100,
        )

        self.assertEqual(
            data["recommendation"]["estimated_group_cost"]["max"],
            "6000.00",
        )

        self.assertEqual(
            data["recommendation"]["conflicts"],
            [],
        )

        self.assertEqual(
            self.client.get(self.url).status_code,
            200,
        )

        self.assertEqual(
            self.post().status_code,
            200,
        )

        self.mock.assert_called_once()

        self.assertEqual(
            self.post(refresh=True).status_code,
            200,
        )

        self.assertEqual(
            self.mock.call_count,
            2,
        )

        self.trip.refresh_from_db()

        self.assertEqual(
            self.trip.destination,
            "",
        )

    def test_read_permissions_and_no_ai_on_get(self):
        self.assertFalse(
            self.client.get(self.url).data["available"]
        )

        self.mock.assert_not_called()

        self.post()

        self.client.force_authenticate(self.member)

        self.assertTrue(
            self.client.get(self.url).data["available"]
        )

        self.assertEqual(
            self.post().status_code,
            404,
        )

        for user in (
            self.pending,
            self.outsider,
        ):
            self.client.force_authenticate(user)

            self.assertEqual(
                self.client.get(self.url).status_code,
                404,
            )

            self.assertEqual(
                self.post().status_code,
                404,
            )

        self.client.force_authenticate(None)

        self.assertEqual(
            self.client.get(self.url).status_code,
            401,
        )

    def test_incomplete_and_different_currency_do_not_call_ai(self):
        answer = TripQuestionnaire.objects.get(
            trip=self.trip,
            user=self.member,
        )

        answer.currency = "USD"
        answer.save()

        self.assertEqual(
            self.post().status_code,
            400,
        )

        answer.delete()

        response = self.post()

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            int(response.data["total_members"]),
            2,
        )

        self.mock.assert_not_called()

    def test_request_validation(self):
        payloads = (
            {},
            {
                "origin_country_code": "Brasil",
            },
            {
                **self.payload,
                "refresh": "true",
            },
            {
                **self.payload,
                "user_id": 1,
            },
        )

        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.url,
                    payload,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    400,
                )

        self.mock.assert_not_called()

    def test_invalid_ai_responses_are_not_saved(self):
        invalid_values = [
            ("cost_min", -1),
            ("cost_max", 1000),
            ("cost_max", True),
            ("cost_max", float("inf")),
            ("cost_max", 10 ** 400),
            ("cost_max", "3000"),
            ("currency", "USD"),
            ("climate", "any"),
            ("city", ""),
            ("reason", ""),
            ("interests", ["inventado"]),
            ("country_code", "BRA"),
        ]

        for field, value in invalid_values:
            with self.subTest(
                field=field,
                value=value,
            ):
                raw = deepcopy(self.raw)

                raw["destinations"][0][field] = value
                self.mock.return_value = raw

                self.assertEqual(
                    self.post().status_code,
                    502,
                )

                self.assertFalse(
                    GroupDestinationRecommendation.objects.exists()
                )

        for raw in (
            None,
            [],
            {},
            {"destinations": []},
            {
                **self.raw,
                "score": 100,
            },
        ):
            self.mock.return_value = raw

            self.assertEqual(
                self.post().status_code,
                502,
            )

    def test_duplicate_and_avoided_destinations_rejected(self):
        self.raw["destinations"][0]["city"] = "Sao Paulo"

        self.assertEqual(
            self.post().status_code,
            502,
        )

        self.raw["destinations"][0]["city"] = "Curitiba"

        TripQuestionnaire.objects.filter(
            user=self.member,
            trip=self.trip,
        ).update(
            avoided_destinations=["são paulo"],
        )

        self.assertEqual(
            self.post().status_code,
            502,
        )

        TripQuestionnaire.objects.filter(
            user=self.member,
            trip=self.trip,
        ).update(
            avoided_destinations=["Brasil"],
        )

        self.assertEqual(
            self.post().status_code,
            502,
        )

    def test_conflicts_are_computed_not_from_ai(self):
        TripQuestionnaire.objects.filter(
            user=self.member,
            trip=self.trip,
        ).update(
            max_budget="1500",
            days=8,
            landscape="beach",
            climate="warm",
            destination_preference="international",
            accommodation="resort",
            pace="relaxed",
            interests=["beach"],
        )

        data = self.post().data["result"]["recommendation"]

        # Integrante: 15 de orçamento + 7,5 de duração = 22,5.
        # Organizadora: 100.
        # Média: 61,25.
        # Resultado: 0,7 × 61,25 + 0,3 × 22,5 = 49,625.

        self.assertEqual(
            data["compatibility"]["score"],
            49.6,
        )

        self.assertEqual(
            data["compatibility"]["label"],
            "low",
        )

        self.assertEqual(
            len(data["conflicts"]),
            8,
        )

        self.assertTrue(
            all(
                conflict["affected_count"] == 1
                and conflict["message"]
                for conflict in data["conflicts"]
            )
        )

    def test_gastronomy_importance_and_any(self):
        TripQuestionnaire.objects.filter(
            trip=self.trip,
        ).update(
            landscape="any",
            climate="any",
            accommodation="any",
            destination_preference="any",
        )

        for candidate in self.raw["destinations"]:
            candidate["interests"] = ["culture"]

        result = self.post().data["result"]["recommendation"]

        self.assertEqual(
            result["compatibility"]["score"],
            83.3,
        )

        self.assertEqual(
            [
                conflict["criterion"]
                for conflict in result["conflicts"]
            ],
            ["interests"],
        )

    def test_stale_results_hidden_after_answers_or_members_change(self):
        self.post()

        TripQuestionnaire.objects.filter(
            user=self.member,
            trip=self.trip,
        ).update(
            notes="Mudou",
        )

        data = self.client.get(self.url).data

        self.assertTrue(data["stale"])
        self.assertIsNone(data["result"])

        self.post()

        TripMembership.objects.filter(
            user=self.member,
            trip=self.trip,
        ).update(
            status="pending",
        )

        self.assertTrue(
            self.client.get(self.url).data["stale"]
        )

        self.client.force_authenticate(self.member)

        self.assertEqual(
            self.client.get(self.url).status_code,
            404,
        )

    def test_concurrent_change_and_provider_failure_preserve_previous_result(self):
        self.post()

        previous = (
            GroupDestinationRecommendation.objects
            .get(trip=self.trip)
            .result
        )

        self.mock.side_effect = GeminiUnavailableError()

        self.assertEqual(
            self.post(refresh=True).status_code,
            503,
        )

        self.assertEqual(
            GroupDestinationRecommendation.objects
            .get(trip=self.trip)
            .result,
            previous,
        )

        def changed(*args, **kwargs):
            TripQuestionnaire.objects.filter(
                user=self.member,
                trip=self.trip,
            ).update(
                notes="Alterado durante geração",
            )

            return self.raw

        self.mock.side_effect = changed

        self.assertEqual(
            self.post(refresh=True).status_code,
            409,
        )

        self.assertEqual(
            GroupDestinationRecommendation.objects
            .get(trip=self.trip)
            .result,
            previous,
        )

    def test_prompt_and_result_do_not_expose_accounts_or_raw_answers(self):
        response = self.post()

        prompt = self.mock.call_args.args[0]

        self.assertNotIn(
            self.owner.email,
            prompt,
        )

        self.assertNotIn(
            '"user_id"',
            prompt,
        )

        self.assertNotIn(
            "Nota privada",
            str(response.data),
        )