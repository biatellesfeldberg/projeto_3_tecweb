from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.gemini import (
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiUnavailableError,
)
from places.models import SavedPlace, TripPlace

from .itinerary import build_itinerary_prompt
from .models import Activity, Trip
from .services import sync_days


User = get_user_model()

GENERATE_JSON = "trips.itinerary.generate_json"


def fake_activity(title, start, category="culture", cost=0, **extra):
    return {
        "title": title,
        "description": f"Descrição de {title}",
        "category": category,
        "start_time": start,
        "duration_minutes": 60,
        "location_name": title,
        "estimated_cost": cost,
        "cost_type": "per_person",
        **extra,
    }


def fake_itinerary(day_count=3):
    days = []
    for number in range(1, day_count + 1):
        days.append({
            "day_number": number,
            "title": f"Dia {number} em Lisboa",
            "activities": [
                fake_activity(
                    "Almoço na Time Out Market",
                    "12:30",
                    category="gastronomy",
                    cost=80,
                    latitude=38.7069,
                    longitude=-9.1458,
                ),
                fake_activity("Mosteiro dos Jerónimos", "09:30", cost=18),
            ],
        })

    return {
        "summary": "Lisboa sem pressa, entre cultura e boa comida.",
        "days": days,
        "lodging": [
            {
                "name": "Hotel Lisboa Centro",
                "area": "Baixa",
                "description": "Perto do metrô.",
                "price_per_night": 650,
                "latitude": 38.71,
                "longitude": -9.14,
            }
        ],
        "estimates": {
            "transport": 16000,
            "lodging": 8400,
            "food": 4200,
            "activities": 3400,
            "notes": "Valores aproximados.",
        },
    }


def make_trip(owner, **fields):
    data = {
        "title": "Lisboa com calma",
        "origin": "São Paulo, Brasil",
        "destination": "Lisboa, Portugal",
        "start_date": date(2027, 5, 12),
        "end_date": date(2027, 5, 14),
        "travelers_count": 4,
        "budget": Decimal("32000.00"),
        "style": Trip.Style.INTERMEDIATE,
        "pace": Trip.Pace.RELAXED,
        "interests": ["culture", "gastronomy"],
    }
    data.update(fields)
    trip = Trip.objects.create(owner=owner, **data)
    sync_days(trip)
    return trip


class ItineraryTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bia", email="bia@exemplo.com", password="senha-forte-123"
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.trip = make_trip(self.user)
        self.url = f"/api/trips/{self.trip.id}/generate-itinerary/"

    def generate(self, body=None):
        return self.client.post(self.url, body or {}, format="json")


class GenerateItineraryTests(ItineraryTestCase):
    @patch(GENERATE_JSON)
    def test_generates_and_saves_full_itinerary(self, generate_json):
        generate_json.return_value = fake_itinerary()

        response = self.generate()

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data["days"]), 3)

        day = data["days"][0]
        self.assertEqual(day["title"], "Dia 1 em Lisboa")
        # Atividades ordenadas por horário, mesmo vindo fora de ordem.
        self.assertEqual(
            [a["title"] for a in day["activities"]],
            ["Mosteiro dos Jerónimos", "Almoço na Time Out Market"],
        )
        lunch = day["activities"][1]
        self.assertEqual(lunch["category"], "gastronomy")
        self.assertEqual(lunch["start_time"], "12:30:00")
        self.assertEqual(lunch["total_cost"], "320.00")
        self.assertEqual(lunch["latitude"], "38.706900")

        self.assertEqual(data["ai_summary"], "Lisboa sem pressa, entre cultura e boa comida.")
        self.assertEqual(data["lodging_suggestions"][0]["name"], "Hotel Lisboa Centro")
        self.assertEqual(data["lodging_suggestions"][0]["price_per_night"], "650.00")
        self.assertEqual(data["cost_estimate"]["total"], "32000.00")
        self.assertEqual(data["cost_estimate"]["per_person"], "8000.00")
        self.assertTrue(data["cost_estimate"]["within_budget"])
        self.assertIsNotNone(data["itinerary_generated_at"])

        # O schema e as instruções foram enviados ao Gemini.
        kwargs = generate_json.call_args.kwargs
        self.assertIn("days", kwargs["schema"]["properties"])
        self.assertIn("Responda sempre em português", kwargs["system_instruction"])

    @patch(GENERATE_JSON)
    def test_replace_existing_removes_old_activities(self, generate_json):
        day = self.trip.days.get(day_number=1)
        Activity.objects.create(day=day, title="Atividade antiga")
        generate_json.return_value = fake_itinerary()

        self.generate({"replace_existing": True})

        self.assertFalse(Activity.objects.filter(title="Atividade antiga").exists())
        self.assertEqual(day.activities.count(), 2)

    @patch(GENERATE_JSON)
    def test_keep_existing_only_fills_empty_days(self, generate_json):
        day = self.trip.days.get(day_number=1)
        day.title = "Meu dia"
        day.save()
        Activity.objects.create(day=day, title="Minha atividade")
        generate_json.return_value = fake_itinerary()

        response = self.generate({"replace_existing": False})

        self.assertEqual(response.status_code, 200)
        first, second = response.data["days"][:2]
        self.assertEqual(first["title"], "Meu dia")
        self.assertEqual([a["title"] for a in first["activities"]], ["Minha atividade"])
        self.assertEqual(len(second["activities"]), 2)

    @patch(GENERATE_JSON)
    def test_keep_existing_with_no_empty_days_does_not_call_ai(self, generate_json):
        for day in self.trip.days.all():
            Activity.objects.create(day=day, title="Já planejado")

        response = self.generate({"replace_existing": False})

        self.assertEqual(response.status_code, 200)
        generate_json.assert_not_called()

    @patch(GENERATE_JSON)
    def test_extra_instructions_go_to_prompt_inside_delimiters(self, generate_json):
        generate_json.return_value = fake_itinerary()

        self.generate({"extra_instructions": "Incluir um dia em Sintra."})

        prompt = generate_json.call_args.args[0]
        self.assertIn(
            "<pedido_do_usuario>Incluir um dia em Sintra.</pedido_do_usuario>",
            prompt,
        )

    def test_extra_instructions_limit(self):
        response = self.generate({"extra_instructions": "x" * 501})
        self.assertEqual(response.status_code, 400)
        self.assertIn("extra_instructions", response.data)

    def test_trip_without_destination_is_rejected(self):
        self.trip.destination = ""
        self.trip.save()

        response = self.generate()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["destination"],
            ["Escolha um destino antes de gerar o roteiro."],
        )

    def test_other_users_trip_is_not_found(self):
        other = User.objects.create_user(
            username="ana", email="ana@exemplo.com", password="senha-forte-123"
        )
        other_trip = make_trip(other)

        response = self.client.post(
            f"/api/trips/{other_trip.id}/generate-itinerary/", {}, format="json"
        )

        self.assertEqual(response.status_code, 404)

    def test_requires_token(self):
        self.client.credentials()
        self.assertEqual(self.generate().status_code, 401)


class GenerateItineraryFailureTests(ItineraryTestCase):
    """Se algo der errado, o roteiro atual não pode ser alterado."""

    def setUp(self):
        super().setUp()
        self.day = self.trip.days.get(day_number=1)
        Activity.objects.create(day=self.day, title="Atividade antiga")

    def assert_itinerary_untouched(self):
        self.assertEqual(
            list(self.day.activities.values_list("title", flat=True)),
            ["Atividade antiga"],
        )
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.itinerary_generated_at)
        self.assertEqual(self.trip.cost_estimate, {})

    @patch(GENERATE_JSON)
    def test_missing_day_is_invalid(self, generate_json):
        generate_json.return_value = fake_itinerary(day_count=2)

        response = self.generate()

        self.assertEqual(response.status_code, 502)
        self.assert_itinerary_untouched()

    @patch(GENERATE_JSON)
    def test_wrong_structure_is_invalid(self, generate_json):
        for bad in (
            {"days": "nenhum"},
            [],
            {**fake_itinerary(), "estimates": "caro"},
        ):
            generate_json.return_value = bad
            response = self.generate()
            self.assertEqual(response.status_code, 502, bad)
        self.assert_itinerary_untouched()

    @patch(GENERATE_JSON)
    def test_all_days_without_activities_is_invalid(self, generate_json):
        data = fake_itinerary()
        for day in data["days"]:
            day["activities"] = [{"title": ""}, "texto solto"]
        generate_json.return_value = data

        self.assertEqual(self.generate().status_code, 502)
        self.assert_itinerary_untouched()

    @patch(GENERATE_JSON)
    def test_ai_errors_keep_itinerary(self, generate_json):
        for error, expected in (
            (GeminiRateLimitError(), 429),
            (GeminiUnavailableError(), 503),
            (GeminiInvalidResponseError(), 502),
        ):
            generate_json.side_effect = error
            response = self.generate()
            self.assertEqual(response.status_code, expected)
            self.assertIn("detail", response.data)
        self.assert_itinerary_untouched()


class ItineraryCleanupTests(ItineraryTestCase):
    """Campos estranhos vindos da IA são corrigidos em vez de quebrar tudo."""

    @patch(GENERATE_JSON)
    def test_bad_fields_are_fixed(self, generate_json):
        data = fake_itinerary()
        data["days"][0]["activities"] = [
            fake_activity(
                "Passeio",
                "25:99",
                category="inventada",
                cost=-10,
                end_time="08:00",
                latitude=200,
                longitude=-9.1,
                cost_type="por pessoa",
                duration_minutes="uma hora",
            ),
            {"title": "   "},
        ]
        data["lodging"].append({"name": "", "price_per_night": 10})
        data["estimates"]["food"] = "muito"
        generate_json.return_value = data

        response = self.generate()

        self.assertEqual(response.status_code, 200)
        activities = response.data["days"][0]["activities"]
        self.assertEqual(len(activities), 1)
        activity = activities[0]
        self.assertEqual(activity["category"], "other")
        self.assertIsNone(activity["start_time"])
        self.assertEqual(activity["estimated_cost"], "0.00")
        self.assertIsNone(activity["latitude"])
        self.assertIsNone(activity["longitude"])
        self.assertEqual(activity["cost_type"], "per_person")
        self.assertIsNone(activity["duration_minutes"])
        self.assertEqual(len(response.data["lodging_suggestions"]), 1)
        self.assertEqual(response.data["cost_estimate"]["food"], "0.00")
        self.assertEqual(response.data["cost_estimate"]["total"], "27800.00")

    @patch(GENERATE_JSON)
    def test_too_many_activities_are_limited(self, generate_json):
        data = fake_itinerary()
        data["days"][0]["activities"] = [
            fake_activity(f"Atividade {n}", f"{8 + n:02d}:00") for n in range(12)
        ]
        generate_json.return_value = data

        response = self.generate()

        self.assertEqual(len(response.data["days"][0]["activities"]), 8)

    @patch(GENERATE_JSON)
    def test_budget_exceeded_is_flagged(self, generate_json):
        self.trip.budget = Decimal("1000.00")
        self.trip.save()
        generate_json.return_value = fake_itinerary()

        response = self.generate()

        self.assertFalse(response.data["cost_estimate"]["within_budget"])


class PromptTests(ItineraryTestCase):
    def test_prompt_has_trip_data_days_and_saved_places(self):
        place = SavedPlace.objects.create(
            owner=self.user,
            name="Palácio da Pena",
            city="Sintra",
            notes="Comprar ingresso antes.",
        )
        TripPlace.objects.create(trip=self.trip, place=place)

        prompt = build_itinerary_prompt(self.trip)

        for expected in (
            "Lisboa, Portugal",
            "São Paulo, Brasil",
            "12/05/2027 a 14/05/2027 (3 dias)",
            "Viajantes: 4",
            "32000.00 BRL",
            "Intermediário",
            "Tranquilo",
            "Cultura, Gastronomia",
            "Dia 1: quarta-feira, 12/05/2027",
            "Dia 3: sexta-feira, 14/05/2027",
            "de 3 a 4 atividades",
            "Palácio da Pena (Sintra): Comprar ingresso antes.",
        ):
            self.assertIn(expected, prompt)


class DestinationSuggestionTests(ItineraryTestCase):
    def setUp(self):
        super().setUp()
        self.trip.destination = ""
        self.trip.save()
        self.url = f"/api/trips/{self.trip.id}/destination-suggestions/"

    @patch(GENERATE_JSON)
    def test_returns_clean_suggestions_without_saving(self, generate_json):
        generate_json.return_value = {
            "suggestions": [
                {
                    "destination": "Lisboa, Portugal",
                    "summary": "Cultura e boa comida.",
                    "reasons": ["Gastronomia", "", "Caminhável", "Barato", "Extra"],
                    "estimated_cost_per_person": 8000,
                    "best_for": ["culture", "gastronomy", "inventado"],
                },
                {
                    "destination": "lisboa, portugal",
                    "summary": "Repetido",
                    "reasons": [],
                    "estimated_cost_per_person": 1,
                },
                {
                    "destination": "Rio de Janeiro, Brasil",
                    "summary": "Praia e cidade.",
                    "reasons": ["Praia"],
                    "estimated_cost_per_person": "barato",
                },
            ]
        }

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        suggestions = response.data["suggestions"]
        self.assertEqual(
            [s["destination"] for s in suggestions],
            ["Lisboa, Portugal", "Rio de Janeiro, Brasil"],
        )
        first = suggestions[0]
        self.assertEqual(first["reasons"], ["Gastronomia", "Caminhável", "Barato"])
        self.assertEqual(first["estimated_cost_per_person"], "8000.00")
        self.assertEqual(first["best_for"], ["culture", "gastronomy"])
        self.assertIsNone(suggestions[1]["estimated_cost_per_person"])

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.destination, "")

    @patch(GENERATE_JSON)
    def test_prompt_uses_profile_reach(self, generate_json):
        self.user.destination_preference = User.DestinationPreference.INTERNATIONAL
        self.user.preferred_destinations = ["Portugal"]
        self.user.save()
        generate_json.return_value = {
            "suggestions": [
                {
                    "destination": "Porto, Portugal",
                    "summary": "x",
                    "reasons": [],
                    "estimated_cost_per_person": 5000,
                }
            ]
        }

        self.client.post(self.url, {}, format="json")

        prompt = generate_json.call_args.args[0]
        self.assertIn("apenas destinos internacionais", prompt)
        self.assertIn("Portugal", prompt)

    @patch(GENERATE_JSON)
    def test_empty_suggestions_are_invalid(self, generate_json):
        generate_json.return_value = {"suggestions": [{"destination": ""}]}

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 502)

    def test_other_users_trip_is_not_found(self):
        other = User.objects.create_user(
            username="ana", email="ana@exemplo.com", password="senha-forte-123"
        )
        other_trip = make_trip(other)

        response = self.client.post(
            f"/api/trips/{other_trip.id}/destination-suggestions/", {}, format="json"
        )

        self.assertEqual(response.status_code, 404)
