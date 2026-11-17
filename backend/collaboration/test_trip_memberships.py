from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from trips.models import Activity, Trip
from trips.services import sync_days

from .models import Friendship, TripMembership


User = get_user_model()


class TripMembershipTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Roteiro!2026Teste",
        )

        cls.b = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="Roteiro!2026Teste",
        )

        cls.c = User.objects.create_user(
            username="luana",
            email="luana@example.com",
            password="Roteiro!2026Teste",
        )

        for user in [cls.a, cls.b, cls.c]:
            Token.objects.create(user=user)

        Friendship.objects.create(
            sender=cls.a,
            recipient=cls.b,
            status="accepted",
        )

        cls.trip = Trip.objects.create(
            owner=cls.a,
            title="Lisboa em grupo",
            origin="São Paulo",
            destination="Lisboa",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 13),
        )

        sync_days(cls.trip)

        cls.day = cls.trip.days.first()

        cls.activity = Activity.objects.create(
            day=cls.day,
            title="Passeio",
        )

    def setUp(self):
        self.auth(self.a)

    def auth(self, user):
        token = Token.objects.get(user=user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

    def invite(self):
        self.auth(self.a)

        return self.client.post(
            f"/api/trips/{self.trip.pk}/members/",
            {"user_id": self.b.pk},
            format="json",
        )

    def accept(self):
        invitation_id = self.invite().data["id"]

        self.auth(self.b)

        response = self.client.post(
            f"/api/trip-invitations/{invitation_id}/accept/"
        )

        self.assertEqual(response.status_code, 200)

        return invitation_id

    def test_owner_invites_friend(self):
        response = self.invite()

        self.assertEqual(response.status_code, 201)

        member = TripMembership.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(member.user_id, self.b.pk)
        self.assertEqual(member.invited_by_id, self.a.pk)
        self.assertEqual(member.status, "pending")

        self.trip.refresh_from_db()

        self.assertEqual(self.trip.mode, "group")
        self.assertEqual(self.trip.travelers_count, 1)

    def test_invite_requires_friendship(self):
        response = self.client.post(
            f"/api/trips/{self.trip.pk}/members/",
            {"user_id": self.c.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TripMembership.objects.exists())

    def test_owner_and_unknown_user_cannot_be_invited(self):
        for user_id in [self.a.pk, 999999]:
            response = self.client.post(
                f"/api/trips/{self.trip.pk}/members/",
                {"user_id": user_id},
                format="json",
            )

            self.assertEqual(response.status_code, 400)

    def test_duplicate_invitation_and_membership(self):
        self.assertEqual(self.invite().status_code, 201)
        self.assertEqual(self.invite().status_code, 400)

        member = TripMembership.objects.get()
        member.status = "accepted"
        member.save()

        self.assertEqual(self.invite().status_code, 400)
        self.assertEqual(TripMembership.objects.count(), 1)

    def test_invitation_is_private_and_does_not_grant_access(self):
        self.invite()
        self.auth(self.b)

        response = self.client.get("/api/trip-invitations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["trip"],
            self.trip.pk,
        )
        self.assertNotIn(
            "email",
            response.data[0]["invited_by"],
        )

        self.assertEqual(
            self.client.get(
                f"/api/trips/{self.trip.pk}/"
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.get(
                f"/api/trips/{self.trip.pk}/members/"
            ).status_code,
            404,
        )

        self.auth(self.c)

        self.assertEqual(
            self.client.get("/api/trip-invitations/").data,
            [],
        )

    def test_accept_grants_read_access(self):
        self.accept()

        response = self.client.get(
            f"/api/trips/{self.trip.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["owner_id"], self.a.pk)

        trips = self.client.get("/api/trips/").data

        self.assertEqual(
            [item["id"] for item in trips],
            [self.trip.pk],
        )

        self.assertEqual(
            self.client.get("/api/trip-invitations/").data,
            [],
        )

        roster = self.client.get(
            f"/api/trips/{self.trip.pk}/members/"
        )

        self.assertEqual(roster.status_code, 200)
        self.assertEqual(
            roster.data["owner"]["id"],
            self.a.pk,
        )
        self.assertEqual(
            roster.data["members"][0]["status"],
            "accepted",
        )

    def test_only_invitee_can_accept_or_reject(self):
        invitation_id = self.invite().data["id"]

        for user in [self.a, self.c]:
            self.auth(user)

            for action in ["accept", "reject"]:
                response = self.client.post(
                    f"/api/trip-invitations/"
                    f"{invitation_id}/{action}/"
                )

                self.assertEqual(response.status_code, 404)

        self.assertEqual(
            TripMembership.objects.get().status,
            "pending",
        )

    def test_reject_and_reinvite(self):
        invitation_id = self.invite().data["id"]

        self.auth(self.b)

        response = self.client.post(
            f"/api/trip-invitations/{invitation_id}/reject/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(TripMembership.objects.exists())

        self.assertEqual(self.invite().status_code, 201)

    def test_owner_cancels_pending_invitation(self):
        invitation_id = self.invite().data["id"]

        response = self.client.delete(
            f"/api/trips/{self.trip.pk}/members/{self.b.pk}/"
        )

        self.assertEqual(response.status_code, 204)

        self.auth(self.b)

        response = self.client.post(
            f"/api/trip-invitations/{invitation_id}/accept/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_removes_participant_and_revokes_access(self):
        self.accept()
        self.auth(self.a)

        response = self.client.delete(
            f"/api/trips/{self.trip.pk}/members/{self.b.pk}/"
        )

        self.assertEqual(response.status_code, 204)

        self.auth(self.b)

        self.assertEqual(
            self.client.get(
                f"/api/trips/{self.trip.pk}/"
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.get("/api/trips/").data,
            [],
        )

        self.assertTrue(
            Trip.objects.filter(pk=self.trip.pk).exists()
        )

    def test_participant_leaves(self):
        self.accept()

        response = self.client.post(
            f"/api/trips/{self.trip.pk}/leave/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertEqual(
            self.client.get(
                f"/api/trips/{self.trip.pk}/"
            ).status_code,
            404,
        )

        self.assertTrue(
            Friendship.objects.filter(
                status="accepted"
            ).exists()
        )

        self.assertTrue(
            Trip.objects.filter(pk=self.trip.pk).exists()
        )

    def test_owner_cannot_leave_or_be_removed(self):
        response = self.client.post(
            f"/api/trips/{self.trip.pk}/leave/"
        )

        self.assertEqual(response.status_code, 400)

        response = self.client.delete(
            f"/api/trips/{self.trip.pk}/members/{self.a.pk}/"
        )

        self.assertEqual(response.status_code, 400)

        self.assertTrue(
            Trip.objects.filter(pk=self.trip.pk).exists()
        )

    def test_participant_cannot_manage_or_modify_trip(self):
        self.accept()

        root = f"/api/trips/{self.trip.pk}/"

        cases = [
            ("patch", root),
            ("delete", root),
            ("post", root + "duplicate/"),
            ("post", root + "generate-itinerary/"),
            ("post", root + "destination-suggestions/"),
            ("post", root + "members/"),
            ("delete", root + f"members/{self.a.pk}/"),
            ("patch", root + f"days/{self.day.pk}/"),
            ("post", root + f"days/{self.day.pk}/reorder/"),
            ("post", root + "activities/"),
            (
                "delete",
                root + f"activities/{self.activity.pk}/",
            ),
        ]

        for method, url in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Trip.objects.filter(pk=self.trip.pk).exists()
        )

        self.assertTrue(
            Activity.objects.filter(pk=self.activity.pk).exists()
        )

    def test_outsider_has_no_access(self):
        self.auth(self.c)

        root = f"/api/trips/{self.trip.pk}/"

        self.assertEqual(
            self.client.get(root).status_code,
            404,
        )

        self.assertEqual(
            self.client.get(root + "members/").status_code,
            404,
        )

        response = self.client.post(
            root + "members/",
            {"user_id": self.b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            self.client.post(root + "leave/").status_code,
            404,
        )

    def test_invitation_cannot_forge_status_or_inviter(self):
        response = self.client.post(
            f"/api/trips/{self.trip.pk}/members/",
            {
                "user_id": self.b.pk,
                "status": "accepted",
                "invited_by": self.c.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TripMembership.objects.exists())

    def test_cannot_set_solo_until_memberships_removed(self):
        self.invite()

        root = f"/api/trips/{self.trip.pk}/"

        response = self.client.patch(
            root,
            {"mode": "solo"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.client.delete(
            root + f"members/{self.b.pk}/"
        )

        response = self.client.patch(
            root,
            {"mode": "solo"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_removing_friendship_does_not_remove_membership(self):
        self.accept()
        self.auth(self.a)

        response = self.client.delete(
            f"/api/friends/{self.b.pk}/"
        )

        self.assertEqual(response.status_code, 204)

        self.auth(self.b)

        self.assertEqual(
            self.client.get(
                f"/api/trips/{self.trip.pk}/"
            ).status_code,
            200,
        )

    def test_database_prevents_duplicate_membership(self):
        self.invite()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TripMembership.objects.create(
                    trip=self.trip,
                    user=self.b,
                    invited_by=self.a,
                )

    def test_all_new_endpoints_require_authentication(self):
        self.client.credentials()

        root = f"/api/trips/{self.trip.pk}/"

        cases = [
            ("get", root + "members/"),
            ("post", root + "members/"),
            ("delete", root + f"members/{self.b.pk}/"),
            ("post", root + "leave/"),
            ("get", "/api/trip-invitations/"),
            ("post", "/api/trip-invitations/999/accept/"),
            ("post", "/api/trip-invitations/999/reject/"),
        ]

        for method, url in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, 401)

    def test_owner_can_still_edit_trip(self):
        self.invite()

        response = self.client.patch(
            f"/api/trips/{self.trip.pk}/",
            {"title": "Nome novo"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Nome novo")