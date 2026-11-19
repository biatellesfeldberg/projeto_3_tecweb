from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from trips.models import Trip

from .models import (
    GroupDestinationRecommendation,
    TripMembership,
    TripQuestionnaire,
)


class DestinationMemberTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.owner = User.objects.create_user(
            username="ana",
            email="ana-test@example.com",
            first_name="Ana",
        )

        self.member = User.objects.create_user(
            username="bia",
            email="bia-test@example.com",
            first_name="Bia",
        )

        self.trip = Trip.objects.create(
            owner=self.owner,
            title="Grupo",
            origin="São Paulo",
            start_date=date(2027, 5, 1),
            end_date=date(2027, 5, 4),
        )

        TripMembership.objects.create(
            trip=self.trip,
            user=self.member,
            invited_by=self.owner,
            status="accepted",
        )

        for user, budget in (
            (self.owner, 5000),
            (self.member, 1500),
        ):
            TripQuestionnaire.objects.create(
                trip=self.trip,
                user=user,
                max_budget=budget,
                days=4,
                landscape="city",
                pace="moderate",
                gastronomy_importance=5,
                destination_preference="domestic",
                climate="mild",
                accommodation="hotel",
                interests=["culture"],
                notes="Privado",
            )

        self.url = (
            f"/api/trips/{self.trip.pk}/"
            "group-destinations/"
        )

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
            "interests": ["culture"],
            "reason": "Cultura no centro.",
            "caveat": "Preços estimados.",
        }

        self.mock = patch(
            "collaboration.destinations.generate_json",
            return_value={
                "destinations": [
                    {
                        **base,
                        "city": city,
                    }
                    for city in (
                        "Curitiba",
                        "São Paulo",
                        "Belo Horizonte",
                    )
                ],
            },
        ).start()

        self.addCleanup(patch.stopall)
        self.client.force_authenticate(self.owner)

    def generate(self):
        return self.client.post(
            self.url,
            {
                "origin_country_code": "BR",
            },
            format="json",
        )

    def test_individual_scores_are_identified_without_raw_answers(self):
        response = self.generate()

        self.assertEqual(
            response.status_code,
            200,
        )

        result = response.data["result"]

        for candidate in [
            result["recommendation"],
            *result["alternatives"],
        ]:
            members = candidate[
                "compatibility"
            ]["members"]

            self.assertEqual(
                [
                    member["user"]["id"]
                    for member in members
                ],
                [
                    self.owner.pk,
                    self.member.pk,
                ],
            )

            self.assertEqual(
                [
                    member["score"]
                    for member in members
                ],
                [100, 85],
            )

            self.assertTrue(
                all(
                    set(member) == {
                        "user",
                        "score",
                        "label",
                    }
                    for member in members
                )
            )

        record = (
            GroupDestinationRecommendation.objects
            .get(trip=self.trip)
        )

        self.assertNotIn(
            "members",
            record.result[
                "recommendation"
            ]["compatibility"],
        )

        self.client.force_authenticate(
            self.member
        )

        self.assertEqual(
            self.client.get(self.url).data["result"],
            result,
        )

        self.mock.assert_called_once()

    def test_old_or_removed_member_results_are_not_shared(self):
        self.generate()

        TripQuestionnaire.objects.filter(
            user=self.member,
        ).update(
            notes="Mudança",
        )

        data = self.client.get(self.url).data

        self.assertTrue(data["stale"])
        self.assertIsNone(data["result"])

        self.generate()

        TripMembership.objects.filter(
            user=self.member,
        ).delete()

        self.assertTrue(
            self.client.get(self.url).data["stale"]
        )

        self.client.force_authenticate(
            self.member
        )

        self.assertEqual(
            self.client.get(self.url).status_code,
            404,
        )