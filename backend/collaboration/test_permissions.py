from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound
from rest_framework.test import APITestCase

from places.models import SavedPlace, TripPlace
from trips.models import Activity, Trip, TripDay
from trips.permissions import (
    accessible_trips_for_user,
    trips_for_user,
    trip_role,
    can_view_trip,
    can_manage_trip,
    trip_participants,
    get_manageable_trip,
)

from .models import (
    Friendship,
    TripMembership,
    TripPoll,
    PollOption,
    PollVote,
    TripQuestionnaire,
)
from .permissions import (
    get_poll_for_trip,
    pending_trip_invitations_for_user,
)

User = get_user_model()


class CollaborativePermissionTests(APITestCase):
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

        for user in [
            cls.owner,
            cls.member,
            cls.pending,
            cls.outsider,
        ]:
            Token.objects.create(user=user)

        cls.trip = Trip.objects.create(
            owner=cls.owner,
            title="Grupo",
            origin="São Paulo",
            destination="Lisboa",
            mode="group",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 14),
            travelers_count=9,
        )

        cls.other = Trip.objects.create(
            owner=cls.member,
            title="Privada da Ana",
            origin="São Paulo",
            start_date=date(2027, 6, 1),
            end_date=date(2027, 6, 2),
        )

        cls.day = TripDay.objects.create(
            trip=cls.trip,
            date=cls.trip.start_date,
            day_number=1,
        )

        cls.other_day = TripDay.objects.create(
            trip=cls.other,
            date=cls.other.start_date,
            day_number=1,
        )

        cls.activity = Activity.objects.create(
            day=cls.day,
            title="Museu",
        )

        cls.other_activity = Activity.objects.create(
            day=cls.other_day,
            title="Passeio privado",
        )

        cls.membership = TripMembership.objects.create(
            trip=cls.trip,
            user=cls.member,
            invited_by=cls.owner,
            status="accepted",
        )

        cls.invitation = TripMembership.objects.create(
            trip=cls.trip,
            user=cls.pending,
            invited_by=cls.owner,
        )

        Friendship.objects.create(
            sender=cls.owner,
            recipient=cls.outsider,
            status="accepted",
        )

        cls.place = SavedPlace.objects.create(
            owner=cls.owner,
            name="Café privado",
            city="Lisboa",
            category="gastronomy",
            notes="Nota pessoal",
        )

        TripPlace.objects.create(
            trip=cls.trip,
            place=cls.place,
        )

        cls.poll = TripPoll.objects.create(
            trip=cls.trip,
            title="Destino",
            category="destination",
        )

        cls.option = PollOption.objects.create(
            poll=cls.poll,
            label="Lisboa",
        )

        PollOption.objects.create(
            poll=cls.poll,
            label="Porto",
        )

        cls.other_poll = TripPoll.objects.create(
            trip=cls.other,
            title="Outra votação",
            category="activity",
        )

        cls.other_option = PollOption.objects.create(
            poll=cls.other_poll,
            label="Praia",
        )

    def setUp(self):
        self.auth(self.owner)
        self.root = f"/api/trips/{self.trip.pk}/"
        self.poll_url = f"{self.root}polls/{self.poll.pk}/"
        self.answer_url = self.root + "questionnaire/me/"

    def auth(self, user):
        token = Token.objects.get(user=user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )

    def request(self, method, url, data=None):
        return getattr(self.client, method)(
            url,
            data=data,
            format="json",
        )

    def reads(self):
        return [
            self.root,
            self.root + "members/",
            self.answer_url,
            self.root + "questionnaire/progress/",
            self.root + "polls/",
            self.poll_url,
        ]

    def management_requests(self):
        return [
            (
                "patch",
                self.root,
                {"title": "Alterado"},
            ),
            (
                "delete",
                self.root,
                None,
            ),
            (
                "post",
                self.root + "duplicate/",
                {},
            ),
            (
                "post",
                self.root + "generate-itinerary/",
                {},
            ),
            (
                "post",
                self.root + "destination-suggestions/",
                {},
            ),
            (
                "patch",
                f"{self.root}days/{self.day.pk}/",
                {"notes": "Alterado"},
            ),
            (
                "post",
                f"{self.root}days/{self.day.pk}/reorder/",
                {"activity_ids": [self.activity.pk]},
            ),
            (
                "post",
                self.root + "activities/",
                {
                    "day": self.day.pk,
                    "title": "Nova",
                },
            ),
            (
                "patch",
                f"{self.root}activities/{self.activity.pk}/",
                {"title": "Alterada"},
            ),
            (
                "delete",
                f"{self.root}activities/{self.activity.pk}/",
                None,
            ),
            (
                "post",
                self.root + "members/",
                {"user_id": self.outsider.pk},
            ),
            (
                "delete",
                f"{self.root}members/{self.pending.pk}/",
                None,
            ),
            (
                "post",
                self.root + "polls/",
                {
                    "title": "Nova",
                    "category": "activity",
                    "options": ["A", "B"],
                },
            ),
            (
                "post",
                self.poll_url + "close/",
                {
                    "option_id": self.option.pk,
                    "reason": "Teste",
                },
            ),
        ]

    def answer(self):
        return {
            "landscape": "city",
            "max_budget": "5000.00",
            "days": 5,
            "pace": "relaxed",
            "gastronomy_importance": 4,
            "destination_preference": "any",
            "climate": "mild",
            "accommodation": "hotel",
            "interests": ["culture"],
        }

    def test_roles_are_specific_to_each_trip(self):
        self.assertEqual(
            trip_role(self.owner, self.trip),
            "owner",
        )
        self.assertEqual(
            trip_role(self.member, self.trip),
            "participant",
        )
        self.assertEqual(
            trip_role(self.member, self.other),
            "owner",
        )

        for user in [
            self.pending,
            self.outsider,
            AnonymousUser(),
        ]:
            self.assertIsNone(trip_role(user, self.trip))

        self.assertTrue(
            can_view_trip(self.member, self.trip)
        )
        self.assertFalse(
            can_manage_trip(self.member, self.trip)
        )
        self.assertTrue(
            can_manage_trip(self.owner, self.trip)
        )

    def test_querysets_and_owner_helper(self):
        self.assertEqual(
            set(accessible_trips_for_user(self.member)),
            {self.trip, self.other},
        )
        self.assertEqual(
            set(trips_for_user(self.member)),
            {self.other},
        )
        self.assertFalse(
            accessible_trips_for_user(AnonymousUser()).exists()
        )
        self.assertFalse(
            trips_for_user(AnonymousUser()).exists()
        )
        self.assertEqual(
            get_manageable_trip(self.owner, self.trip.pk),
            self.trip,
        )

        with self.assertRaises(NotFound):
            get_manageable_trip(self.member, self.trip.pk)

    def test_participants_exclude_pending_and_travelers_count(self):
        self.assertEqual(
            set(trip_participants(self.trip)),
            {self.owner, self.member},
        )

    def test_owner_can_edit_trip(self):
        response = self.client.patch(
            self.root,
            {"title": "Novo nome"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.title, "Novo nome")

    def test_accepted_member_can_read_shared_resources(self):
        self.auth(self.member)

        for url in self.reads():
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    200,
                )

    def test_pending_and_outsider_cannot_read_trip(self):
        for user in [self.pending, self.outsider]:
            self.auth(user)

            for url in self.reads():
                with self.subTest(user=user.pk, url=url):
                    self.assertEqual(
                        self.client.get(url).status_code,
                        404,
                    )

    def test_list_only_contains_accessible_trips(self):
        cases = [
            (self.owner, {self.trip.pk}),
            (self.member, {self.trip.pk, self.other.pk}),
            (self.pending, set()),
            (self.outsider, set()),
        ]

        for user, expected in cases:
            self.auth(user)
            response = self.client.get("/api/trips/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                {item["id"] for item in response.data},
                expected,
            )

    def test_nonowners_cannot_manage_shared_trip(self):
        for user in [
            self.member,
            self.pending,
            self.outsider,
        ]:
            self.auth(user)

            for method, url, data in self.management_requests():
                with self.subTest(
                    user=user.pk,
                    method=method,
                    url=url,
                ):
                    response = self.request(method, url, data)
                    self.assertEqual(response.status_code, 404)

        self.trip.refresh_from_db()
        self.activity.refresh_from_db()

        self.assertEqual(self.trip.title, "Grupo")
        self.assertEqual(self.activity.title, "Museu")
        self.assertFalse(PollVote.objects.exists())

    def test_nested_resources_must_belong_to_trip(self):
        self.auth(self.member)
        root = f"/api/trips/{self.other.pk}/"

        requests = [
            (
                "patch",
                f"{root}days/{self.day.pk}/",
                {"notes": "Invasão"},
            ),
            (
                "patch",
                f"{root}activities/{self.activity.pk}/",
                {"title": "Invasão"},
            ),
            (
                "get",
                f"{root}polls/{self.poll.pk}/",
                None,
            ),
            (
                "put",
                f"{root}polls/{self.poll.pk}/vote/",
                {"option_id": self.option.pk},
            ),
        ]

        for method, url, data in requests:
            response = self.request(method, url, data)
            self.assertEqual(response.status_code, 404)

        with self.assertRaises(NotFound):
            get_poll_for_trip(self.other, self.poll.pk)

    def test_invitation_scope_is_personal(self):
        self.assertEqual(
            list(pending_trip_invitations_for_user(self.pending)),
            [self.invitation],
        )
        self.assertFalse(
            pending_trip_invitations_for_user(self.owner).exists()
        )
        self.assertFalse(
            pending_trip_invitations_for_user(AnonymousUser()).exists()
        )

        for user in [
            self.owner,
            self.member,
            self.outsider,
        ]:
            self.auth(user)

            self.assertEqual(
                self.client.get("/api/trip-invitations/").data,
                [],
            )

            for action in ["accept", "reject"]:
                url = (
                    f"/api/trip-invitations/"
                    f"{self.invitation.pk}/{action}/"
                )

                self.assertEqual(
                    self.client.post(url).status_code,
                    404,
                )

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, "pending")

    def test_questionnaire_is_always_own(self):
        self.client.put(
            self.answer_url,
            self.answer(),
            format="json",
        )

        self.auth(self.member)

        response = self.client.get(
            self.answer_url + f"?user_id={self.owner.pk}"
        )

        self.assertEqual(
            response.data,
            {"answered": False, "answers": None},
        )

        response = self.client.put(
            self.answer_url,
            self.answer(),
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.patch(
            self.answer_url,
            {"days": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            TripQuestionnaire.objects.get(
                user=self.owner,
                trip=self.trip,
            ).days,
            5,
        )

        for field in ["user", "trip"]:
            response = self.client.patch(
                self.answer_url,
                {field: self.owner.pk},
                format="json",
            )
            self.assertEqual(response.status_code, 400)

        progress = self.client.get(
            self.root + "questionnaire/progress/"
        ).data

        self.assertEqual(progress["answered_count"], 2)
        self.assertNotIn("max_budget", str(progress))

    def test_vote_identity_comes_from_token(self):
        self.auth(self.member)

        response = self.client.put(
            self.poll_url + "vote/",
            {"option_id": self.option.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            PollVote.objects.get().user_id,
            self.member.pk,
        )

        response = self.client.put(
            self.poll_url + "vote/",
            {
                "option_id": self.option.pk,
                "user_id": self.owner.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PollVote.objects.count(), 1)

    def test_poll_option_must_belong_to_poll(self):
        self.auth(self.member)

        response = self.client.put(
            self.poll_url + "vote/",
            {"option_id": self.other_option.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(PollVote.objects.exists())

    def test_removal_revokes_access_with_same_token(self):
        response = self.client.delete(
            f"{self.root}members/{self.member.pk}/"
        )
        self.assertEqual(response.status_code, 204)

        self.auth(self.member)

        for url in self.reads():
            self.assertEqual(
                self.client.get(url).status_code,
                404,
            )

        response = self.client.put(
            self.answer_url,
            self.answer(),
            format="json",
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.put(
            self.poll_url + "vote/",
            {"option_id": self.option.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            {
                item["id"]
                for item in self.client.get("/api/trips/").data
            },
            {self.other.pk},
        )

        self.assertEqual(
            self.client.get("/api/auth/me/").status_code,
            200,
        )

    def test_leaving_revokes_access(self):
        self.auth(self.member)

        response = self.client.post(self.root + "leave/")
        self.assertEqual(response.status_code, 204)

        for url in self.reads():
            self.assertEqual(
                self.client.get(url).status_code,
                404,
            )

        self.assertIsNone(
            trip_role(self.member, self.trip)
        )

    def test_private_places_are_not_shared_by_membership(self):
        for user in [
            self.member,
            self.pending,
            self.outsider,
        ]:
            self.auth(user)

            self.assertEqual(
                self.client.get("/api/places/").data,
                [],
            )

            for method in ["get", "patch", "delete"]:
                data = (
                    {"notes": "Invasão"}
                    if method == "patch"
                    else None
                )

                response = self.request(
                    method,
                    f"/api/places/{self.place.pk}/",
                    data,
                )

                self.assertEqual(response.status_code, 404)

            self.assertEqual(
                self.client.get(
                    self.root + "places/"
                ).status_code,
                404,
            )

        self.place.refresh_from_db()
        self.assertEqual(self.place.notes, "Nota pessoal")

    def test_member_cannot_link_private_place_to_shared_trip(self):
        self.auth(self.member)

        response = self.client.post(
            "/api/places/",
            {
                "name": "Meu café",
                "city": "Lisboa",
                "category": "gastronomy",
                "trip_ids": [self.trip.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_friendship_alone_does_not_grant_trip_access(self):
        self.auth(self.outsider)

        self.assertIsNone(
            trip_role(self.outsider, self.trip)
        )

        self.assertEqual(
            self.client.get(self.root).status_code,
            404,
        )

    def test_anonymous_cannot_access_collaborative_endpoints(self):
        self.client.credentials()

        requests = (
            [("get", url, None) for url in self.reads()]
            + self.management_requests()
            + [
                (
                    "put",
                    self.answer_url,
                    self.answer(),
                ),
                (
                    "patch",
                    self.answer_url,
                    {"days": 3},
                ),
                (
                    "put",
                    self.poll_url + "vote/",
                    {"option_id": self.option.pk},
                ),
                (
                    "post",
                    self.root + "leave/",
                    None,
                ),
                (
                    "get",
                    "/api/trip-invitations/",
                    None,
                ),
                (
                    "post",
                    (
                        f"/api/trip-invitations/"
                        f"{self.invitation.pk}/accept/"
                    ),
                    None,
                ),
                (
                    "post",
                    (
                        f"/api/trip-invitations/"
                        f"{self.invitation.pk}/reject/"
                    ),
                    None,
                ),
            ]
        )

        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                response = self.request(method, url, data)
                self.assertEqual(response.status_code, 401)