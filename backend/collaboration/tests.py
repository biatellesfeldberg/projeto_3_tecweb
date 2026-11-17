from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Friendship


User = get_user_model()


class FriendshipTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            first_name="Bia",
            password="Roteiro!2026Teste",
        )

        cls.b = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            first_name="Ana",
            password="Roteiro!2026Teste",
        )

        cls.c = User.objects.create_user(
            username="luana",
            email="luana@example.com",
            first_name="Luana",
            password="Roteiro!2026Teste",
        )

        for user in [cls.a, cls.b, cls.c]:
            Token.objects.create(user=user)

    def setUp(self):
        self.auth(self.a)

    def auth(self, user):
        token = Token.objects.get(user=user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

    def send(self):
        return self.client.post(
            "/api/friend-requests/",
            {"recipient_id": self.b.pk},
            format="json",
        )

    def test_search(self):
        self.assertEqual(
            self.client.get("/api/users/").data,
            [],
        )

        response = self.client.get(
            "/api/users/?search=ana@example.com"
        )

        self.assertEqual(response.status_code, 200)

        ids = [user["id"] for user in response.data]

        self.assertIn(self.b.pk, ids)
        self.assertNotIn(self.a.pk, ids)

        self.assertEqual(
            set(response.data[0]),
            {"id", "first_name", "last_name"},
        )

    def test_send_and_pending_lists(self):
        response = self.send()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["sender"]["id"],
            self.a.pk,
        )
        self.assertEqual(response.data["status"], "pending")

        data = self.client.get("/api/friend-requests/").data
        self.assertEqual(len(data["sent"]), 1)

        self.auth(self.b)

        data = self.client.get("/api/friend-requests/").data

        self.assertEqual(len(data["received"]), 1)
        self.assertEqual(data["sent"], [])

        self.auth(self.c)

        self.assertEqual(
            self.client.get("/api/friend-requests/").data,
            {"received": [], "sent": []},
        )

    def test_invalid_recipient(self):
        for value in [self.a.pk, 999999, 0, "invalid"]:
            with self.subTest(value=value):
                response = self.client.post(
                    "/api/friend-requests/",
                    {"recipient_id": value},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/friend-requests/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Friendship.objects.exists())

    def test_inactive_recipient(self):
        self.b.is_active = False
        self.b.save()

        self.assertEqual(self.send().status_code, 400)

        response = self.client.get(
            "/api/users/?search=ana@example.com"
        )

        self.assertEqual(response.data, [])

    def test_duplicate_and_reverse_requests(self):
        self.send()

        self.assertEqual(self.send().status_code, 400)

        self.auth(self.b)

        response = self.client.post(
            "/api/friend-requests/",
            {"recipient_id": self.a.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Friendship.objects.count(), 1)

    def test_sender_and_status_cannot_be_forged(self):
        response = self.client.post(
            "/api/friend-requests/",
            {
                "recipient_id": self.b.pk,
                "sender": self.c.pk,
                "status": "accepted",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Friendship.objects.exists())

    def test_recipient_accepts_and_both_become_friends(self):
        request_id = self.send().data["id"]

        self.auth(self.b)

        response = self.client.post(
            f"/api/friend-requests/{request_id}/accept/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.client.get("/api/friends/").data[0]["id"],
            self.a.pk,
        )

        self.assertEqual(
            self.client.get(
                "/api/friend-requests/"
            ).data["received"],
            [],
        )

        self.auth(self.a)

        self.assertEqual(
            self.client.get("/api/friends/").data[0]["id"],
            self.b.pk,
        )

        self.assertEqual(self.send().status_code, 400)

    def test_sender_cannot_accept_or_reject(self):
        request_id = self.send().data["id"]

        for action in ["accept", "reject"]:
            response = self.client.post(
                f"/api/friend-requests/{request_id}/{action}/"
            )

            self.assertEqual(response.status_code, 404)

        self.assertEqual(
            Friendship.objects.get(pk=request_id).status,
            "pending",
        )

    def test_outsider_cannot_change_request(self):
        request_id = self.send().data["id"]

        self.auth(self.c)

        for action in ["accept", "reject"]:
            response = self.client.post(
                f"/api/friend-requests/{request_id}/{action}/"
            )

            self.assertEqual(response.status_code, 404)

        response = self.client.delete(
            f"/api/friend-requests/{request_id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            Friendship.objects.get(pk=request_id).status,
            "pending",
        )

    def test_recipient_rejects_and_new_request_is_allowed(self):
        request_id = self.send().data["id"]

        self.auth(self.b)

        response = self.client.post(
            f"/api/friend-requests/{request_id}/reject/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Friendship.objects.exists())

        self.auth(self.a)

        self.assertEqual(self.send().status_code, 201)

    def test_only_sender_can_cancel(self):
        request_id = self.send().data["id"]

        self.auth(self.b)

        response = self.client.delete(
            f"/api/friend-requests/{request_id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.auth(self.a)

        response = self.client.delete(
            f"/api/friend-requests/{request_id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Friendship.objects.exists())

    def test_pending_is_not_friendship(self):
        self.send()

        self.assertEqual(
            self.client.get("/api/friends/").data,
            [],
        )

    def test_either_friend_can_remove_friendship(self):
        pairs = [
            (self.a, self.b),
            (self.b, self.a),
        ]

        for user, other in pairs:
            link = Friendship.objects.create(
                sender=self.a,
                recipient=self.b,
                status="accepted",
            )

            self.auth(user)

            response = self.client.delete(
                f"/api/friends/{other.pk}/"
            )

            self.assertEqual(response.status_code, 204)

            self.assertFalse(
                Friendship.objects.filter(pk=link.pk).exists()
            )

    def test_cannot_remove_self_or_unrelated_friendship(self):
        link = Friendship.objects.create(
            sender=self.a,
            recipient=self.b,
            status="accepted",
        )

        response = self.client.delete(
            f"/api/friends/{self.a.pk}/"
        )

        self.assertEqual(response.status_code, 404)

        self.auth(self.c)

        response = self.client.delete(
            f"/api/friends/{self.b.pk}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Friendship.objects.filter(pk=link.pk).exists()
        )

    def test_accepted_request_cannot_be_changed_as_pending(self):
        link = Friendship.objects.create(
            sender=self.a,
            recipient=self.b,
            status="accepted",
        )

        response = self.client.delete(
            f"/api/friend-requests/{link.pk}/"
        )

        self.assertEqual(response.status_code, 404)

        self.auth(self.b)

        for action in ["accept", "reject"]:
            response = self.client.post(
                f"/api/friend-requests/{link.pk}/{action}/"
            )

            self.assertEqual(response.status_code, 404)

    def test_endpoints_require_token(self):
        self.client.credentials()

        cases = [
            ("get", "/api/users/?search=Ana"),
            ("get", "/api/friends/"),
            ("get", "/api/friend-requests/"),
            ("post", "/api/friend-requests/"),
            ("delete", f"/api/friends/{self.b.pk}/"),
            ("post", "/api/friend-requests/999/accept/"),
            ("post", "/api/friend-requests/999/reject/"),
            ("delete", "/api/friend-requests/999/"),
        ]

        for method, url in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, 401)

    def test_database_blocks_reverse_pair(self):
        Friendship.objects.create(
            sender=self.a,
            recipient=self.b,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    sender=self.b,
                    recipient=self.a,
                )

    def test_database_blocks_self_friendship(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    sender=self.a,
                    recipient=self.a,
                )