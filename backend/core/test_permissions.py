import io
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.test import override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound
from rest_framework.test import APITestCase

from places.models import SavedPlace, TripPlace
from trips.models import Activity, Trip, TripDay
from trips.permissions import (
    get_user_activity,
    get_user_day,
    get_user_trip,
    trips_for_user,
)


User = get_user_model()


class PrivacyTests(APITestCase):
    def setUp(self):
        temporary_media = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_media.cleanup)

        settings_override = override_settings(
            MEDIA_ROOT=temporary_media.name,
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.a = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Viagem!2026Segura",
            first_name="Bia",
        )

        self.b = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="Outra!Senha2026Segura",
            first_name="Ana",
        )

        self.token_a = Token.objects.create(user=self.a)
        self.token_b = Token.objects.create(user=self.b)

        trip_data = {
            "origin": "São Paulo",
            "start_date": date(2027, 5, 12),
            "end_date": date(2027, 5, 13),
        }

        self.trip_a = Trip.objects.create(
            owner=self.a,
            title="Viagem da Bia",
            **trip_data,
        )

        self.trip_b = Trip.objects.create(
            owner=self.b,
            title="Viagem privada da Ana",
            **trip_data,
        )

        self.place_a = SavedPlace.objects.create(
            owner=self.a,
            name="Café da Bia",
        )

        self.place_b = SavedPlace.objects.create(
            owner=self.b,
            name="Café da Ana",
        )

        self.day_a = TripDay.objects.create(
            trip=self.trip_a,
            date=date(2027, 5, 12),
            day_number=1,
        )

        self.day_b = TripDay.objects.create(
            trip=self.trip_b,
            date=date(2027, 5, 12),
            day_number=1,
        )

        self.activity_a = Activity.objects.create(
            day=self.day_a,
            title="Passeio da Bia",
        )

        self.activity_b = Activity.objects.create(
            day=self.day_b,
            title="Passeio da Ana",
        )

        self.authenticate(self.token_a)

    def authenticate(self, token):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

    def test_profile_uses_authenticated_user(self):
        response = self.client.get(
            f"/api/auth/me/?user_id={self.b.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.a.pk)
        self.assertNotIn("password", response.data)

        self.authenticate(self.token_b)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.data["id"], self.b.pk)

    def test_cannot_choose_target_profile_or_permissions(self):
        attempts = [
            ("id", self.b.pk),
            ("user_id", self.b.pk),
            ("email", self.b.email),
            ("is_staff", True),
            ("is_superuser", True),
        ]

        for field, value in attempts:
            with self.subTest(field=field):
                response = self.client.patch(
                    "/api/auth/me/",
                    {field: value},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

        self.a.refresh_from_db()
        self.b.refresh_from_db()

        self.assertFalse(self.a.is_staff)
        self.assertFalse(self.a.is_superuser)
        self.assertEqual(self.b.email, "ana@example.com")

    def test_place_list_hides_other_users_data(self):
        response = self.client.get("/api/places/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.place_a.pk],
        )

        response = self.client.get(
            "/api/places/?search=Ana"
        )

        self.assertEqual(response.data, [])

    def test_cannot_read_edit_delete_other_place(self):
        url = f"/api/places/{self.place_b.pk}/"

        for method in ["get", "patch", "delete"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    url,
                    {"name": "Alterado"},
                    format="json",
                )

                self.assertEqual(response.status_code, 404)

        self.place_b.refresh_from_db()

        self.assertEqual(self.place_b.name, "Café da Ana")

    def test_place_owner_is_set_by_backend(self):
        response = self.client.post(
            "/api/places/",
            {
                "name": "Lugar novo",
                "owner": self.b.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        place = SavedPlace.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(place.owner_id, self.a.pk)

        response = self.client.patch(
            f"/api/places/{self.place_a.pk}/",
            {"owner": self.b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.place_a.refresh_from_db()

        self.assertEqual(self.place_a.owner_id, self.a.pk)

    def test_other_trip_links_are_inaccessible(self):
        TripPlace.objects.create(
            trip=self.trip_b,
            place=self.place_b,
        )

        url = f"/api/trips/{self.trip_b.pk}/places/"

        self.assertEqual(
            self.client.get(url).status_code,
            404,
        )

        response = self.client.post(
            url,
            {"place_ids": [self.place_a.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        response = self.client.delete(
            url + f"{self.place_b.pk}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            TripPlace.objects.filter(
                trip=self.trip_b,
                place=self.place_b,
            ).exists()
        )

    def test_cannot_link_own_place_to_other_trip(self):
        response = self.client.patch(
            f"/api/places/{self.place_a.pk}/",
            {"trip_ids": [self.trip_b.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.place_a.trips.exists())

    def test_cannot_link_other_place_to_own_trip(self):
        response = self.client.post(
            f"/api/trips/{self.trip_a.pk}/places/",
            {
                "place_ids": [
                    self.place_a.pk,
                    self.place_b.pk,
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            TripPlace.objects.filter(
                trip=self.trip_a,
            ).exists()
        )

    def test_nested_trip_summary_hides_private_trip(self):
        TripPlace.objects.create(
            trip=self.trip_a,
            place=self.place_a,
        )

        # Simula um vínculo inconsistente criado fora da API.
        TripPlace.objects.create(
            trip=self.trip_b,
            place=self.place_a,
        )

        response = self.client.get(
            f"/api/places/{self.place_a.pk}/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["trips"],
            [
                {
                    "id": self.trip_a.pk,
                    "title": self.trip_a.title,
                }
            ],
        )

    def test_trip_helpers_filter_by_owner(self):
        self.assertEqual(
            list(trips_for_user(self.a)),
            [self.trip_a],
        )

        self.assertFalse(
            trips_for_user(AnonymousUser()).exists()
        )

        self.assertEqual(
            get_user_trip(self.a, self.trip_a.pk),
            self.trip_a,
        )

        with self.assertRaises(NotFound):
            get_user_trip(self.a, self.trip_b.pk)

    def test_day_and_activity_must_belong_to_accessible_trip(self):
        self.assertEqual(
            get_user_day(
                self.a,
                self.trip_a.pk,
                self.day_a.pk,
            ),
            self.day_a,
        )

        self.assertEqual(
            get_user_activity(
                self.a,
                self.trip_a.pk,
                self.activity_a.pk,
            ),
            self.activity_a,
        )

        for trip_id in [self.trip_a.pk, self.trip_b.pk]:
            with self.assertRaises(NotFound):
                get_user_day(
                    self.a,
                    trip_id,
                    self.day_b.pk,
                )

            with self.assertRaises(NotFound):
                get_user_activity(
                    self.a,
                    trip_id,
                    self.activity_b.pk,
                )

    def test_all_existing_private_routes_require_token(self):
        self.client.credentials()

        cases = [
            ("get", "/api/auth/me/"),
            ("patch", "/api/auth/me/"),
            ("get", "/api/auth/me/photo/"),
            ("patch", "/api/auth/me/photo/"),
            ("delete", "/api/auth/me/photo/"),
            ("get", "/api/places/"),
            ("post", "/api/places/"),
            ("get", f"/api/places/{self.place_a.pk}/"),
            ("patch", f"/api/places/{self.place_a.pk}/"),
            ("delete", f"/api/places/{self.place_a.pk}/"),
            ("get", f"/api/trips/{self.trip_a.pk}/places/"),
            ("post", f"/api/trips/{self.trip_a.pk}/places/"),
            (
                "delete",
                f"/api/trips/{self.trip_a.pk}/places/"
                f"{self.place_a.pk}/",
            ),
        ]

        for method, url in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, 401)

    def test_invalid_and_revoked_tokens_do_not_work(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Token invalid",
        )

        self.assertEqual(
            self.client.get("/api/auth/me/").status_code,
            401,
        )

        self.authenticate(self.token_a)

        self.assertEqual(
            self.client.post("/api/auth/logout/").status_code,
            200,
        )

        self.assertEqual(
            self.client.get("/api/places/").status_code,
            401,
        )

    def test_photo_is_private_and_uses_current_user(self):
        def image_bytes(color):
            output = io.BytesIO()
            Image.new("RGB", (10, 10), color).save(
                output,
                "PNG",
            )
            return output.getvalue()

        content_a = image_bytes("blue")
        content_b = image_bytes("red")

        self.a.photo.save(
            "bia.png",
            ContentFile(content_a),
            save=True,
        )

        self.b.photo.save(
            "ana.png",
            ContentFile(content_b),
            save=True,
        )

        public_url = self.a.photo.url

        response = self.client.get("/api/auth/me/")

        self.assertEqual(
            response.data["photo"],
            "http://testserver/api/auth/me/photo/",
        )

        response = self.client.get(
            f"/api/auth/me/photo/?user_id={self.b.pk}"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            b"".join(response.streaming_content),
            content_a,
        )

        response.close()

        self.client.credentials()

        self.assertEqual(
            self.client.get(
                "/api/auth/me/photo/"
            ).status_code,
            401,
        )

        self.assertEqual(
            self.client.get(public_url).status_code,
            404,
        )

    def test_photo_delete_cannot_target_other_user(self):
        output = io.BytesIO()

        Image.new("RGB", (10, 10), "red").save(
            output,
            "PNG",
        )

        self.b.photo.save(
            "ana.png",
            ContentFile(output.getvalue()),
            save=True,
        )

        response = self.client.delete(
            f"/api/auth/me/photo/?user_id={self.b.pk}"
        )

        self.assertEqual(response.status_code, 200)

        self.b.refresh_from_db()

        self.assertTrue(
            self.b.photo.storage.exists(
                self.b.photo.name
            )
        )