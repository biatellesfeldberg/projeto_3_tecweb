from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from trips.models import Trip
from .models import TripMembership, TripPoll, PollOption, PollVote

User = get_user_model()


class PollTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.member, cls.pending, cls.outsider = [
            User.objects.create_user(
                username=name,
                email=f"{name}@example.com",
                password="Teste!2026Rumo",
            )
            for name in ["bia", "ana", "luana", "renata"]
        ]

        cls.trip = Trip.objects.create(
            owner=cls.owner,
            title="Grupo",
            origin="São Paulo",
            mode="group",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 14),
            travelers_count=8,
        )

        for user, state in [
            (cls.member, "accepted"),
            (cls.pending, "pending"),
        ]:
            TripMembership.objects.create(
                trip=cls.trip,
                user=user,
                invited_by=cls.owner,
                status=state,
            )

    def setUp(self):
        self.client.force_authenticate(self.owner)

        self.base = f"/api/trips/{self.trip.pk}/polls/"

        response = self.client.post(
            self.base,
            {
                "title": "Qual destino?",
                "category": "destination",
                "options": ["Lisboa", "Porto"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.poll_id = response.data["id"]
        self.first, self.second = [
            option["id"]
            for option in response.data["options"]
        ]

        self.detail = f"{self.base}{self.poll_id}/"

    def vote(self, user, option=None):
        self.client.force_authenticate(user)

        return self.client.put(
            self.detail + "vote/",
            {"option_id": option or self.first},
            format="json",
        )

    def close(self, option=None):
        self.client.force_authenticate(self.owner)

        return self.client.post(
            self.detail + "close/",
            {
                "option_id": option or self.first,
                "reason": "Decisão do grupo.",
            },
            format="json",
        )

    def test_create_and_list(self):
        response = self.client.get(self.base)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["total_votes"], 0)
        self.assertIsNone(response.data[0]["decision"])

    def test_invalid_creation(self):
        cases = [
            {"options": ["Lisboa"]},
            {"options": ["Lisboa", " lisboa "]},
            {"options": ["A"] * 11},
            {"options": ["", "Porto"]},
            {"category": "invalid"},
            {"title": ""},
            {"status": "closed"},
        ]

        for extra in cases:
            with self.subTest(extra=extra):
                data = {
                    "title": "Destino",
                    "category": "destination",
                    "options": ["A", "B"],
                    **extra,
                }

                response = self.client.post(
                    self.base,
                    data,
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

        self.assertEqual(TripPoll.objects.count(), 1)

    def test_member_can_read_and_vote_but_not_manage(self):
        self.assertEqual(
            self.vote(self.member).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(self.detail).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                self.base,
                {},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                self.detail + "close/",
                {},
                format="json",
            ).status_code,
            404,
        )

    def test_pending_and_outsider_denied(self):
        for user in [self.pending, self.outsider]:
            self.client.force_authenticate(user)

            requests = [
                ("get", self.base, None),
                ("get", self.detail, None),
                ("post", self.base, {}),
                (
                    "put",
                    self.detail + "vote/",
                    {"option_id": self.first},
                ),
                ("post", self.detail + "close/", {}),
            ]

            for method, url, data in requests:
                with self.subTest(
                    user=user.pk,
                    method=method,
                    url=url,
                ):
                    response = getattr(
                        self.client,
                        method,
                    )(url, data, format="json")

                    self.assertEqual(response.status_code, 404)

    def test_anonymous_denied(self):
        self.client.force_authenticate(None)

        requests = [
            ("get", self.base),
            ("post", self.base),
            ("get", self.detail),
            ("put", self.detail + "vote/"),
            ("post", self.detail + "close/"),
        ]

        for method, url in requests:
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 401)

    def test_repeat_vote_and_change_do_not_duplicate(self):
        self.vote(self.owner)
        self.vote(self.owner)

        response = self.vote(self.owner, self.second)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_votes"], 1)
        self.assertEqual(response.data["my_vote"], self.second)
        self.assertEqual(
            [item["votes"] for item in response.data["options"]],
            [0, 1],
        )
        self.assertEqual(PollVote.objects.count(), 1)

    def test_two_users_count_separately(self):
        self.vote(self.owner)
        response = self.vote(self.member)

        self.assertEqual(response.data["total_votes"], 2)
        self.assertEqual(
            response.data["options"][0]["votes"],
            2,
        )
        self.assertNotIn(
            "user",
            response.data["options"][0],
        )

    def test_identity_forgery_rejected(self):
        response = self.client.put(
            self.detail + "vote/",
            {
                "option_id": self.first,
                "user_id": self.member.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PollVote.objects.exists())

    def test_foreign_option_rejected(self):
        other = TripPoll.objects.create(
            trip=self.trip,
            title="Outra",
            category="activity",
        )

        option = PollOption.objects.create(
            poll=other,
            label="Museu",
        )

        self.assertEqual(
            self.vote(self.owner, option.pk).status_code,
            404,
        )
        self.assertFalse(PollVote.objects.exists())

        self.vote(self.owner)

        self.assertEqual(
            self.close(option.pk).status_code,
            404,
        )

    def test_poll_cannot_be_accessed_under_another_trip(self):
        other = Trip.objects.create(
            owner=self.owner,
            title="Outra",
            origin="São Paulo",
            start_date=date(2027, 6, 1),
            end_date=date(2027, 6, 2),
        )

        url = (
            f"/api/trips/{other.pk}/polls/"
            f"{self.poll_id}/"
        )

        self.assertEqual(
            self.client.get(url).status_code,
            404,
        )

        response = self.client.put(
            url + "vote/",
            {"option_id": self.first},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_close_requires_votes_reason_and_leading_option(self):
        self.assertEqual(self.close().status_code, 400)

        self.vote(self.owner)

        self.assertEqual(
            self.close(self.second).status_code,
            400,
        )

        response = self.client.post(
            self.detail + "close/",
            {
                "option_id": self.first,
                "reason": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            TripPoll.objects.get(pk=self.poll_id).status,
            "open",
        )

    def test_tie_can_be_resolved_and_closed_poll_is_immutable(self):
        self.vote(self.owner)
        self.vote(self.member, self.second)

        response = self.close(self.second)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "closed")
        self.assertIsNotNone(response.data["closed_at"])
        self.assertEqual(
            response.data["decision"]["option_id"],
            self.second,
        )
        self.assertEqual(
            response.data["decision"]["reason"],
            "Decisão do grupo.",
        )

        self.assertEqual(
            self.vote(self.owner).status_code,
            400,
        )
        self.assertEqual(self.close().status_code, 400)

        response = self.client.patch(
            self.detail,
            {"title": "Alterado"},
            format="json",
        )
        self.assertEqual(response.status_code, 405)

        self.assertEqual(
            self.client.delete(self.detail).status_code,
            405,
        )

    def test_leaving_excludes_vote_from_open_tally(self):
        self.vote(self.owner)
        self.vote(self.member, self.second)

        response = self.client.post(
            f"/api/trips/{self.trip.pk}/leave/"
        )

        self.assertEqual(response.status_code, 204)

        self.client.force_authenticate(self.owner)
        response = self.client.get(self.detail)

        self.assertEqual(response.data["total_votes"], 1)
        self.assertEqual(
            [item["votes"] for item in response.data["options"]],
            [1, 0],
        )

        self.assertEqual(
            self.close(self.second).status_code,
            400,
        )

    def test_removing_member_does_not_change_closed_result(self):
        self.vote(self.member)
        closed = self.close().data

        response = self.client.delete(
            f"/api/trips/{self.trip.pk}/members/"
            f"{self.member.pk}/"
        )

        self.assertEqual(response.status_code, 204)

        response = self.client.get(self.detail)

        self.assertEqual(
            response.data["decision"],
            closed["decision"],
        )
        self.assertEqual(response.data["total_votes"], 1)

        self.client.force_authenticate(self.member)

        self.assertEqual(
            self.client.get(self.detail).status_code,
            404,
        )

    def test_rejoining_recovers_vote_in_open_poll(self):
        self.vote(self.member)

        membership = TripMembership.objects.get(
            trip=self.trip,
            user=self.member,
        )

        membership.status = "pending"
        membership.save()

        self.client.force_authenticate(self.owner)

        self.assertEqual(
            self.client.get(self.detail).data["total_votes"],
            0,
        )

        membership.status = "accepted"
        membership.save()

        self.assertEqual(
            self.client.get(self.detail).data["total_votes"],
            1,
        )

    def test_database_prevents_duplicate_vote(self):
        self.vote(self.owner)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PollVote.objects.create(
                    poll_id=self.poll_id,
                    user=self.owner,
                    option_id=self.second,
                )