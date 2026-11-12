from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from trips.models import Trip

from .models import SavedPlace, TripPlace


User = get_user_model()


class PlacesTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Viagem!2026Segura",
        )
        self.other_user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="Outra!Senha2026Segura",
        )

        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        self.trip = Trip.objects.create(
            owner=self.user,
            title="Lisboa com calma",
            origin="São Paulo",
            destination="Lisboa",
            start_date=date(2027, 5, 12),
            end_date=date(2027, 5, 18),
        )
        self.other_trip = Trip.objects.create(
            owner=self.other_user,
            title="Viagem da Ana",
            origin="Recife",
            destination="Rio de Janeiro",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 1, 12),
        )

    def create_place(self, owner=None, **fields):
        data = {"name": "Um café em Alfama", "city": "Lisboa"}
        data.update(fields)
        return SavedPlace.objects.create(owner=owner or self.user, **data)


class PlaceCrudTests(PlacesTestCase):
    def test_exige_autenticacao(self):
        self.client.credentials()

        response = self.client.get("/api/places/")

        self.assertEqual(response.status_code, 401)

    def test_cadastrar_lugar(self):
        response = self.client.post(
            "/api/places/",
            {
                "name": "Palácio da Pena",
                "city": "Sintra",
                "country": "Portugal",
                "category": "culture",
                "notes": "Comprar ingresso antes.",
                "latitude": "38.787600",
                "longitude": "-9.390400",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Palácio da Pena")
        self.assertEqual(response.data["category"], "culture")
        self.assertEqual(response.data["notes"], "Comprar ingresso antes.")
        self.assertEqual(response.data["latitude"], "38.787600")
        self.assertEqual(response.data["trips"], [])
        self.assertNotIn("trip_ids", response.data)

        place = SavedPlace.objects.get(id=response.data["id"])
        self.assertEqual(place.owner, self.user)

    def test_cadastro_usa_valores_padrao(self):
        response = self.client.post(
            "/api/places/", {"name": "Copacabana"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["category"], "other")
        self.assertEqual(response.data["city"], "")
        self.assertIsNone(response.data["latitude"])
        self.assertIsNone(response.data["longitude"])

    def test_cadastro_exige_nome(self):
        response = self.client.post(
            "/api/places/", {"name": "  ", "city": "Lisboa"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

    def test_cadastro_recusa_categoria_invalida(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Lugar", "category": "praia"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data)

    def test_coordenadas_precisam_vir_juntas(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Lugar", "latitude": "38.7"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("latitude", response.data)

    def test_coordenadas_fora_do_intervalo(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Lugar", "latitude": "91", "longitude": "10"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("latitude", response.data)

    def test_coordenadas_com_mais_casas_sao_arredondadas(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Lugar", "latitude": 38.71141234, "longitude": -9.13770009},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["latitude"], "38.711412")
        self.assertEqual(response.data["longitude"], "-9.137700")

    def test_listar_apenas_os_proprios_lugares(self):
        self.create_place(name="Meu lugar")
        self.create_place(owner=self.other_user, name="Lugar da Ana")

        response = self.client.get("/api/places/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["name"] for p in response.data], ["Meu lugar"])

    def test_listar_sem_lugares(self):
        response = self.client.get("/api/places/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_consultar_lugar(self):
        place = self.create_place()

        response = self.client.get(f"/api/places/{place.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], place.id)

    def test_lugar_de_outra_pessoa_responde_404(self):
        place = self.create_place(owner=self.other_user)

        for method in ("get", "patch", "delete"):
            response = getattr(self.client, method)(
                f"/api/places/{place.id}/", {}, format="json"
            )
            self.assertEqual(response.status_code, 404, method)
            self.assertEqual(response.data, {"detail": "Não encontrado."})

        self.assertTrue(SavedPlace.objects.filter(id=place.id).exists())

    def test_editar_lugar(self):
        place = self.create_place(category="gastronomy")

        response = self.client.patch(
            f"/api/places/{place.id}/",
            {"notes": "Ir no fim da tarde.", "category": "culture"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notes"], "Ir no fim da tarde.")
        self.assertEqual(response.data["category"], "culture")
        self.assertEqual(response.data["name"], "Um café em Alfama")

    def test_editar_nao_troca_o_dono(self):
        place = self.create_place()

        self.client.patch(
            f"/api/places/{place.id}/",
            {"owner": self.other_user.id},
            format="json",
        )

        place.refresh_from_db()
        self.assertEqual(place.owner, self.user)

    def test_editar_uma_coordenada_mantem_a_outra(self):
        place = self.create_place(latitude="38.7", longitude="-9.1")

        response = self.client.patch(
            f"/api/places/{place.id}/", {"latitude": "38.8"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["latitude"], "38.800000")
        self.assertEqual(response.data["longitude"], "-9.100000")

    def test_remover_uma_so_coordenada_e_recusado(self):
        place = self.create_place(latitude="38.7", longitude="-9.1")

        response = self.client.patch(
            f"/api/places/{place.id}/", {"latitude": None}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_remover_lugar(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.delete(f"/api/places/{place.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(SavedPlace.objects.filter(id=place.id).exists())
        self.assertFalse(TripPlace.objects.exists())
        self.assertTrue(Trip.objects.filter(id=self.trip.id).exists())


class PlaceFilterTests(PlacesTestCase):
    def setUp(self):
        super().setUp()
        self.cafe = self.create_place(
            name="Um café em Alfama", city="Lisboa", category="gastronomy"
        )
        self.pena = self.create_place(
            name="Palácio da Pena",
            city="Sintra",
            category="culture",
            notes="Perto de Lisboa",
        )
        self.copa = self.create_place(
            name="Um dia em Copacabana", city="Rio de Janeiro", category="beach"
        )
        TripPlace.objects.create(trip=self.trip, place=self.cafe)

    def names(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return sorted(place["name"] for place in response.data)

    def test_busca_por_nome_cidade_ou_observacoes(self):
        self.assertEqual(
            self.names("/api/places/?search=lisboa"),
            ["Palácio da Pena", "Um café em Alfama"],
        )
        self.assertEqual(
            self.names("/api/places/?search=copa"), ["Um dia em Copacabana"]
        )

    def test_filtro_por_categoria(self):
        self.assertEqual(
            self.names("/api/places/?category=culture"), ["Palácio da Pena"]
        )

    def test_filtro_por_categoria_invalida(self):
        response = self.client.get("/api/places/?category=xyz")

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data)

    def test_filtro_por_cidade(self):
        self.assertEqual(
            self.names("/api/places/?city=rio de janeiro"),
            ["Um dia em Copacabana"],
        )

    def test_filtro_por_viagem(self):
        self.assertEqual(
            self.names(f"/api/places/?trip={self.trip.id}"),
            ["Um café em Alfama"],
        )

    def test_filtro_sem_viagem(self):
        self.assertEqual(
            self.names("/api/places/?trip=none"),
            ["Palácio da Pena", "Um dia em Copacabana"],
        )

    def test_filtro_por_viagem_invalido(self):
        response = self.client.get("/api/places/?trip=abc")

        self.assertEqual(response.status_code, 400)

    def test_filtros_combinados(self):
        self.assertEqual(
            self.names("/api/places/?search=um&category=beach"),
            ["Um dia em Copacabana"],
        )

    def test_lugar_em_varias_viagens_aparece_uma_vez(self):
        second_trip = Trip.objects.create(
            owner=self.user,
            title="Outra",
            origin="São Paulo",
            start_date=date(2027, 8, 1),
            end_date=date(2027, 8, 2),
        )
        TripPlace.objects.create(trip=second_trip, place=self.cafe)

        response = self.client.get("/api/places/?search=alfama")

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            [trip["title"] for trip in response.data[0]["trips"]],
            ["Lisboa com calma", "Outra"],
        )


class PlaceTripIdsTests(PlacesTestCase):
    def test_cadastrar_ja_vinculado_a_viagem(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Pastéis de Belém", "trip_ids": [self.trip.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["trips"],
            [{"id": self.trip.id, "title": "Lisboa com calma"}],
        )

    def test_nao_vincula_viagem_de_outra_pessoa(self):
        response = self.client.post(
            "/api/places/",
            {"name": "Lugar", "trip_ids": [self.other_trip.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("trip_ids", response.data)
        self.assertFalse(SavedPlace.objects.exists())

    def test_editar_substitui_as_viagens(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.patch(
            f"/api/places/{place.id}/", {"trip_ids": []}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["trips"], [])
        self.assertFalse(TripPlace.objects.exists())

    def test_editar_sem_trip_ids_mantem_as_viagens(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.patch(
            f"/api/places/{place.id}/", {"notes": "Oi"}, format="json"
        )

        self.assertEqual(len(response.data["trips"]), 1)


class TripPlacesTests(PlacesTestCase):
    def test_listar_lugares_da_viagem(self):
        place = self.create_place()
        self.create_place(name="Fora da viagem")
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.get(f"/api/trips/{self.trip.id}/places/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.data], [place.id])

    def test_vincular_varios_lugares(self):
        first = self.create_place(name="Primeiro")
        second = self.create_place(name="Segundo")

        response = self.client.post(
            f"/api/trips/{self.trip.id}/places/",
            {"place_ids": [first.id, second.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [p["id"] for p in response.data], [first.id, second.id]
        )
        self.assertEqual(self.trip.saved_places.count(), 2)

    def test_vincular_de_novo_nao_duplica(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.post(
            f"/api/trips/{self.trip.id}/places/",
            {"place_ids": [place.id, place.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(TripPlace.objects.count(), 1)

    def test_vincular_exige_lista(self):
        response = self.client.post(
            f"/api/trips/{self.trip.id}/places/",
            {"place_ids": []},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("place_ids", response.data)

    def test_nao_vincula_lugar_de_outra_pessoa(self):
        mine = self.create_place()
        theirs = self.create_place(owner=self.other_user)

        response = self.client.post(
            f"/api/trips/{self.trip.id}/places/",
            {"place_ids": [mine.id, theirs.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("place_ids", response.data)
        self.assertFalse(TripPlace.objects.exists())

    def test_viagem_de_outra_pessoa_responde_404(self):
        place = self.create_place()
        url = f"/api/trips/{self.other_trip.id}/places/"

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(
                url, {"place_ids": [place.id]}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"{url}{place.id}/").status_code, 404
        )
        self.assertFalse(TripPlace.objects.exists())

    def test_viagem_inexistente_responde_404(self):
        response = self.client.get("/api/trips/9999/places/")

        self.assertEqual(response.status_code, 404)

    def test_desvincular_lugar(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        response = self.client.delete(
            f"/api/trips/{self.trip.id}/places/{place.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(TripPlace.objects.exists())
        self.assertTrue(SavedPlace.objects.filter(id=place.id).exists())

    def test_desvincular_lugar_nao_vinculado_responde_404(self):
        place = self.create_place()

        response = self.client.delete(
            f"/api/trips/{self.trip.id}/places/{place.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_excluir_viagem_remove_vinculos_mas_mantem_lugares(self):
        place = self.create_place()
        TripPlace.objects.create(trip=self.trip, place=place)

        self.trip.delete()

        self.assertFalse(TripPlace.objects.exists())
        self.assertTrue(SavedPlace.objects.filter(id=place.id).exists())
