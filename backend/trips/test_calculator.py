from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from collaboration.models import TripMembership
from core.gemini import GeminiRateLimitError

from .calculator import breakdown, max_days_for_budget
from .models import Trip
from .serializers import MAX_TRIP_DAYS
from .test_itinerary import make_trip


User = get_user_model()

GENERATE_JSON = "trips.calculator.generate_json"


def fake_rates(**changes):
    rates = {
        "transport_round_trip": 16000,
        "lodging_per_night": 600,
        "food_per_person_per_day": 150,
        "activities_per_person_per_day": 80,
        "local_transport_per_person_per_day": 30,
        "notes": "Valores de média temporada.",
    }
    rates.update(changes)
    return rates


def decimal_rates(**changes):
    return {
        key: Decimal(str(value))
        for key, value in fake_rates(**changes).items()
        if key != "notes"
    }


class CalculatorMathTests(APITestCase):
    """Contas feitas pelo backend, sem a IA."""

    def test_breakdown_for_three_days(self):
        nights, categories, total = breakdown(decimal_rates(), 4, 3)

        self.assertEqual(nights, 2)
        self.assertEqual(categories["transport"], Decimal("16360.00"))
        self.assertEqual(categories["lodging"], Decimal("1200.00"))
        self.assertEqual(categories["food"], Decimal("1800.00"))
        self.assertEqual(categories["activities"], Decimal("960.00"))
        self.assertEqual(total, Decimal("20320.00"))

    def test_one_day_trip_has_no_lodging(self):
        nights, categories, _ = breakdown(decimal_rates(), 2, 1)

        self.assertEqual(nights, 0)
        self.assertEqual(categories["lodging"], Decimal("0.00"))

    def test_max_days_is_the_longest_trip_that_fits(self):
        rates = decimal_rates()

        days = max_days_for_budget(rates, 4, Decimal("32000"))

        self.assertEqual(days, 10)
        self.assertLessEqual(breakdown(rates, 4, 10)[2], Decimal("32000"))
        self.assertGreater(breakdown(rates, 4, 11)[2], Decimal("32000"))

    def test_exact_budget_fits(self):
        rates = decimal_rates()
        exact = breakdown(rates, 4, 5)[2]

        self.assertEqual(max_days_for_budget(rates, 4, exact), 5)
        self.assertEqual(max_days_for_budget(rates, 4, exact - Decimal("0.01")), 4)

    def test_budget_below_one_day_returns_zero(self):
        self.assertEqual(
            max_days_for_budget(decimal_rates(), 4, Decimal("10000")), 0
        )

    def test_days_are_capped(self):
        self.assertEqual(
            max_days_for_budget(decimal_rates(), 1, Decimal("99999999")),
            MAX_TRIP_DAYS,
        )


class CostCalculatorApiTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="luana", email="luana@exemplo.com", password="senha-forte-123"
        )
        self.authenticate(self.user)
        self.trip = make_trip(self.user)
        self.url = f"/api/trips/{self.trip.id}/cost-calculator/"

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def calculate(self, body):
        return self.client.post(self.url, body, format="json")


class DurationModeTests(CostCalculatorApiTestCase):
    @patch(GENERATE_JSON)
    def test_estimates_cost_for_given_days(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["mode"], "duration")
        self.assertEqual(data["days"], 3)
        self.assertEqual(data["nights"], 2)
        self.assertEqual(data["travelers_count"], 4)
        self.assertEqual(data["currency"], "BRL")
        self.assertEqual(
            data["categories"],
            {
                "transport": "16360.00",
                "lodging": "1200.00",
                "food": "1800.00",
                "activities": "960.00",
            },
        )
        self.assertEqual(data["total"], "20320.00")
        self.assertEqual(data["per_person"], "5080.00")
        self.assertEqual(data["per_day"], "6773.33")
        # Compara com o orçamento cadastrado na viagem.
        self.assertEqual(data["budget"], "32000.00")
        self.assertTrue(data["within_budget"])
        self.assertEqual(data["remaining"], "11680.00")
        self.assertEqual(data["minimum_cost"], "17040.00")
        self.assertEqual(data["rates"]["lodging_per_night"], "600.00")
        self.assertEqual(data["rates"]["notes"], "Valores de média temporada.")

    @patch(GENERATE_JSON)
    def test_uses_trip_duration_when_days_not_sent(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "duration"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["days"], self.trip.duration_days)

    @patch(GENERATE_JSON)
    def test_trip_without_budget_has_no_comparison(self, generate_json):
        generate_json.return_value = fake_rates()
        self.trip.budget = None
        self.trip.save()

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["budget"])
        self.assertIsNone(response.data["within_budget"])
        self.assertIsNone(response.data["remaining"])

    @patch(GENERATE_JSON)
    def test_over_budget(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "duration", "days": 20})

        self.assertFalse(response.data["within_budget"])
        self.assertTrue(response.data["remaining"].startswith("-"))

    def test_rejects_invalid_days(self):
        for days in (0, MAX_TRIP_DAYS + 1, "abc"):
            response = self.calculate({"mode": "duration", "days": days})
            self.assertEqual(response.status_code, 400)
            self.assertIn("days", response.data)


class BudgetModeTests(CostCalculatorApiTestCase):
    @patch(GENERATE_JSON)
    def test_finds_possible_duration(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "budget", "budget": "32000.00"})

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["mode"], "budget")
        self.assertEqual(data["days"], 10)
        self.assertEqual(data["nights"], 9)
        self.assertEqual(data["total"], "31800.00")
        self.assertEqual(data["remaining"], "200.00")
        self.assertTrue(data["within_budget"])
        self.assertFalse(data["max_days_reached"])
        self.assertEqual(
            sum(Decimal(value) for value in data["categories"].values()),
            Decimal(data["total"]),
        )

    @patch(GENERATE_JSON)
    def test_uses_trip_budget_when_not_sent(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "budget"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["budget"], "32000.00")
        self.assertEqual(response.data["days"], 10)

    def test_requires_budget_when_trip_has_none(self):
        self.trip.budget = None
        self.trip.save()

        response = self.calculate({"mode": "budget"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("budget", response.data)

    @patch(GENERATE_JSON)
    def test_budget_too_small(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "budget", "budget": "10000"})

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["days"], 0)
        self.assertEqual(data["total"], "0.00")
        self.assertIsNone(data["per_day"])
        self.assertFalse(data["within_budget"])
        # Faltam 7040 para o mínimo de um dia (17040).
        self.assertEqual(data["remaining"], "-7040.00")

    @patch(GENERATE_JSON)
    def test_huge_budget_is_capped(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate({"mode": "budget", "budget": "9999999"})

        self.assertEqual(response.data["days"], MAX_TRIP_DAYS)
        self.assertTrue(response.data["max_days_reached"])

    def test_rejects_invalid_budget(self):
        for budget in ("0", "-10", "abc"):
            response = self.calculate({"mode": "budget", "budget": budget})
            self.assertEqual(response.status_code, 400)
            self.assertIn("budget", response.data)


class CostRatesCacheTests(CostCalculatorApiTestCase):
    @patch(GENERATE_JSON)
    def test_reuses_rates_between_calculations(self, generate_json):
        generate_json.return_value = fake_rates()

        self.calculate({"mode": "duration", "days": 3})
        self.calculate({"mode": "duration", "days": 7})
        self.calculate({"mode": "budget", "budget": "20000"})

        self.assertEqual(generate_json.call_count, 1)

    @patch(GENERATE_JSON)
    def test_refresh_asks_again(self, generate_json):
        generate_json.return_value = fake_rates()
        self.calculate({"mode": "duration", "days": 3})

        generate_json.return_value = fake_rates(lodging_per_night=900)
        response = self.calculate({"mode": "duration", "days": 3, "refresh": True})

        self.assertEqual(generate_json.call_count, 2)
        self.assertEqual(response.data["categories"]["lodging"], "1800.00")

    @patch(GENERATE_JSON)
    def test_trip_changes_invalidate_rates(self, generate_json):
        generate_json.return_value = fake_rates()
        self.calculate({"mode": "duration", "days": 3})

        self.client.patch(
            f"/api/trips/{self.trip.id}/",
            {"destination": "Porto, Portugal"},
            format="json",
        )
        self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(generate_json.call_count, 2)
        self.assertIn("Porto, Portugal", generate_json.call_args.args[0])

    @patch(GENERATE_JSON)
    def test_style_can_be_simulated(self, generate_json):
        generate_json.return_value = fake_rates()

        response = self.calculate(
            {"mode": "duration", "days": 3, "style": "comfort"}
        )

        self.assertEqual(response.data["style"], "comfort")
        self.assertIn("Conforto", generate_json.call_args.args[0])
        # Simular outro estilo não altera a viagem.
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.style, Trip.Style.INTERMEDIATE)

    @patch(GENERATE_JSON)
    def test_prompt_uses_itinerary_estimate(self, generate_json):
        generate_json.return_value = fake_rates()
        self.trip.cost_estimate = {
            "transport": "16000.00",
            "lodging": "8400.00",
            "food": "4200.00",
            "activities": "3400.00",
            "total": "32000.00",
        }
        self.trip.save()

        self.calculate({"mode": "duration", "days": 3})

        prompt = generate_json.call_args.args[0]
        self.assertIn("hospedagem 8400.00", prompt)
        self.assertIn("São Paulo, Brasil", prompt)
        self.assertIn("Viajantes: 4", prompt)


class InvalidAiResponseTests(CostCalculatorApiTestCase):
    @patch(GENERATE_JSON)
    def test_missing_or_invalid_values_are_rejected(self, generate_json):
        bad_responses = [
            fake_rates(lodging_per_night=None),
            fake_rates(food_per_person_per_day=-5),
            fake_rates(lodging_per_night=0),
            fake_rates(transport_round_trip="muito"),
            ["não é um objeto"],
        ]

        for bad in bad_responses:
            generate_json.return_value = bad
            response = self.calculate({"mode": "duration", "days": 3})
            self.assertEqual(response.status_code, 502, bad)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.cost_rates, {})

    @patch(GENERATE_JSON)
    def test_ai_failure_keeps_previous_rates(self, generate_json):
        generate_json.return_value = fake_rates()
        self.calculate({"mode": "duration", "days": 3})
        saved = Trip.objects.get(id=self.trip.id).cost_rates

        generate_json.side_effect = GeminiRateLimitError()
        response = self.calculate({"mode": "duration", "days": 3, "refresh": True})

        self.assertEqual(response.status_code, 429)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.cost_rates, saved)

    @patch(GENERATE_JSON)
    def test_zero_transport_is_allowed_in_the_same_city(self, generate_json):
        self.trip.destination = "Sao Paulo, SP"
        self.trip.save()
        generate_json.return_value = fake_rates(transport_round_trip=0)

        response = self.calculate({"mode": "duration", "days": 1})

        self.assertEqual(response.status_code, 200)

    @patch(GENERATE_JSON)
    def test_zero_transport_between_cities_is_rejected(self, generate_json):
        generate_json.return_value = fake_rates(transport_round_trip=0)

        response = self.calculate({"mode": "duration", "days": 1})

        self.assertEqual(response.status_code, 502)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.cost_rates, {})

    @patch(GENERATE_JSON)
    def test_prompt_asks_for_stable_values_per_transport(self, generate_json):
        generate_json.return_value = fake_rates()

        self.calculate({"mode": "duration", "days": 3})

        prompt = generate_json.call_args.args[0]
        self.assertIn("preços médios de mercado", prompt)
        self.assertIn("multiplicado pelo número de viajantes", prompt)
        self.assertIn("combustível e os pedágios", prompt)
        self.assertEqual(generate_json.call_args.kwargs["temperature"], 0.2)


class CostCalculatorPermissionTests(CostCalculatorApiTestCase):
    def test_requires_destination(self):
        self.trip.destination = ""
        self.trip.save()

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.data)

    def test_requires_valid_mode(self):
        response = self.calculate({"mode": "outro"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("mode", response.data)

    def test_requires_authentication(self):
        self.client.credentials()

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 401)

    @patch(GENERATE_JSON)
    def test_other_users_get_404(self, generate_json):
        stranger = User.objects.create_user(
            username="outra", email="outra@exemplo.com", password="senha-forte-123"
        )
        self.authenticate(stranger)

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 404)
        generate_json.assert_not_called()

    @patch(GENERATE_JSON)
    def test_pending_invitation_gets_404(self, generate_json):
        guest = User.objects.create_user(
            username="convidada", email="convidada@exemplo.com",
            password="senha-forte-123",
        )
        TripMembership.objects.create(
            trip=self.trip, user=guest, invited_by=self.user
        )
        self.authenticate(guest)

        response = self.calculate({"mode": "duration", "days": 3})

        self.assertEqual(response.status_code, 404)
        generate_json.assert_not_called()

    @patch(GENERATE_JSON)
    def test_accepted_participant_can_calculate(self, generate_json):
        generate_json.return_value = fake_rates()
        member = User.objects.create_user(
            username="amiga", email="amiga@exemplo.com", password="senha-forte-123"
        )
        TripMembership.objects.create(
            trip=self.trip, user=member, invited_by=self.user, status="accepted"
        )
        self.authenticate(member)

        response = self.calculate({"mode": "budget", "budget": "32000"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["days"], 10)

    def test_trip_dates_unchanged(self):
        with patch(GENERATE_JSON, return_value=fake_rates()):
            self.calculate({"mode": "duration", "days": 9})

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, date(2027, 5, 12))
        self.assertEqual(self.trip.end_date, date(2027, 5, 14))
        self.assertEqual(self.trip.days.count(), 3)
