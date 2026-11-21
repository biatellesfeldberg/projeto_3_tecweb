from datetime import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from collaboration.models import PollOption, TripMembership, TripPoll
from core.gemini import GeminiInvalidResponseError, GeminiUnavailableError
from places.models import SavedPlace, TripPlace

from .models import Activity, ItineraryProposal
from .replanning import compare_day
from .test_itinerary import fake_activity, make_trip


User = get_user_model()

GENERATE_JSON = "trips.replanning.generate_json"

ESTIMATES = {
    "transport": 16000,
    "lodging": 8400,
    "food": 4600,
    "activities": 3000,
    "notes": "Depois do ajuste.",
}


def fake_proposal(day_numbers=(1, 2, 3), **changes):
    data = {
        "summary": "Lisboa com um dia em Sintra.",
        "changes": ["Dia 2: Sintra entrou no lugar do museu, como pedido."],
        "days": [
            {
                "day_number": number,
                "title": f"Dia {number} ajustado",
                "activities": [
                    fake_activity("Café na Pastelaria", "09:00", "gastronomy", 15),
                    fake_activity(
                        "Palácio da Pena" if number == 2 else "Mosteiro dos Jerónimos",
                        "10:30",
                        cost=20,
                        latitude=38.7876,
                        longitude=-9.3906,
                    ),
                ],
            }
            for number in day_numbers
        ],
        "estimates": ESTIMATES,
    }
    data.update(changes)
    return data


class ReplanTestCase(APITestCase):
    def setUp(self):
        self.owner = self.make_user("luana")
        self.authenticate(self.owner)
        self.trip = make_trip(self.owner)
        self.days = list(self.trip.days.order_by("date"))

        for day in self.days:
            Activity.objects.create(
                day=day,
                title="Mosteiro dos Jerónimos",
                category="culture",
                start_time=time(10, 30),
                estimated_cost=Decimal("18.00"),
                order=1,
            )
            Activity.objects.create(
                day=day,
                title="Museu do Azulejo",
                category="culture",
                start_time=time(15, 0),
                order=2,
            )

        self.trip.cost_estimate = {"total": "30000.00"}
        self.trip.ai_summary = "Resumo antigo."
        self.trip.save()

        self.url = f"/api/trips/{self.trip.id}/proposals/"

    def make_user(self, name):
        return User.objects.create_user(
            username=name, email=f"{name}@exemplo.com", password="senha-forte-123"
        )

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def add_member(self, name="amiga", accepted=True):
        member = self.make_user(name)
        TripMembership.objects.create(
            trip=self.trip,
            user=member,
            invited_by=self.owner,
            status="accepted" if accepted else "pending",
        )
        return member

    def propose(self, body=None):
        return self.client.post(
            self.url, body or {"request": "Quero um dia em Sintra."}, format="json"
        )

    def titles(self, day):
        return list(day.activities.order_by("order").values_list("title", flat=True))


class CreateProposalTests(ReplanTestCase):
    @patch(GENERATE_JSON)
    def test_creates_proposal_without_changing_itinerary(self, generate_json):
        generate_json.return_value = fake_proposal()
        before = [self.titles(day) for day in self.days]

        response = self.propose()

        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["request"], "Quero um dia em Sintra.")
        self.assertEqual(data["summary"], "Lisboa com um dia em Sintra.")
        self.assertEqual(len(data["changes"]), 1)
        self.assertEqual(data["estimates"]["total"], "32000.00")
        self.assertEqual(data["current_estimate"], {"total": "30000.00"})
        self.assertTrue(data["can_apply"])
        self.assertTrue(data["can_discard"])
        self.assertFalse(data["is_outdated"])

        # O roteiro atual continua igual até a confirmação.
        self.assertEqual([self.titles(day) for day in self.days], before)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.ai_summary, "Resumo antigo.")

    @patch(GENERATE_JSON)
    def test_compares_with_current_itinerary(self, generate_json):
        generate_json.return_value = fake_proposal()

        day = self.propose().data["days"][1]

        self.assertEqual(day["day_number"], 2)
        self.assertEqual(day["current_title"], "")
        self.assertEqual(day["proposed_title"], "Dia 2 ajustado")
        self.assertEqual(
            [item["title"] for item in day["current"]],
            ["Mosteiro dos Jerónimos", "Museu do Azulejo"],
        )
        self.assertEqual(
            [item["title"] for item in day["proposed"]],
            ["Café na Pastelaria", "Palácio da Pena"],
        )
        self.assertEqual(day["added"], ["Café na Pastelaria", "Palácio da Pena"])
        self.assertEqual(
            day["removed"], ["Mosteiro dos Jerónimos", "Museu do Azulejo"]
        )
        self.assertEqual(day["kept"], [])
        self.assertTrue(day["changed"])
        self.assertEqual(day["proposed"][1]["start_time"], "10:30:00")
        self.assertEqual(day["proposed"][1]["latitude"], "38.787600")

    @patch(GENERATE_JSON)
    def test_prompt_has_itinerary_request_places_and_decisions(self, generate_json):
        generate_json.return_value = fake_proposal()

        place = SavedPlace.objects.create(
            owner=self.owner,
            name="Palácio da Pena",
            city="Sintra",
            country="Portugal",
            category="culture",
        )
        linked = SavedPlace.objects.create(
            owner=self.owner, name="LX Factory", city="Lisboa"
        )
        TripPlace.objects.create(trip=self.trip, place=linked)

        poll = TripPoll.objects.create(
            trip=self.trip,
            title="Jantar de sexta",
            category="restaurant",
            status="closed",
            closed_at=timezone.now(),
            decision={"label": "Cervejaria Ramiro", "reason": "Mais votado"},
        )
        PollOption.objects.create(poll=poll, label="Cervejaria Ramiro")
        TripPoll.objects.create(
            trip=self.trip, title="Ainda aberta", category="activity"
        )

        response = self.propose({
            "request": "Quero um dia em Sintra.",
            "place_ids": [place.id],
        })

        prompt = generate_json.call_args.args[0]
        self.assertIn("Lisboa, Portugal", prompt)
        self.assertIn("Museu do Azulejo", prompt)
        self.assertIn("<pedido_do_usuario>Quero um dia em Sintra.</pedido_do_usuario>", prompt)
        self.assertIn("DEVEM entrar", prompt)
        self.assertIn("Palácio da Pena [culture] (Sintra, Portugal)", prompt)
        self.assertIn("LX Factory", prompt)
        self.assertIn('"Jantar de sexta": escolhido Cervejaria Ramiro', prompt)
        self.assertNotIn("Ainda aberta", prompt)

        self.assertEqual(response.data["place_ids"], [place.id])
        self.assertEqual(response.data["decisions"][0]["choice"], "Cervejaria Ramiro")

    @patch(GENERATE_JSON)
    def test_only_selected_days_can_change(self, generate_json):
        generate_json.return_value = fake_proposal(day_numbers=(2,))
        day = self.days[1]

        response = self.propose({"request": "Mais leve", "day_ids": [day.id]})

        self.assertEqual(response.status_code, 201)
        self.assertEqual([d["day_id"] for d in response.data["days"]], [day.id])
        prompt = generate_json.call_args.args[0]
        self.assertIn("exatamente os dias 2 ", prompt)
        self.assertEqual(prompt.count("[PODE MUDAR]"), 1)
        self.assertEqual(prompt.count("[NÃO MUDAR]"), 2)

    @patch(GENERATE_JSON)
    def test_extra_days_from_ai_are_ignored(self, generate_json):
        generate_json.return_value = fake_proposal(day_numbers=(1, 2, 3))

        response = self.propose({"request": "Mais leve", "day_ids": [self.days[0].id]})

        self.assertEqual(len(response.data["days"]), 1)

    @patch(GENERATE_JSON)
    def test_new_proposal_supersedes_previous(self, generate_json):
        generate_json.return_value = fake_proposal()
        first = self.propose().data["id"]

        second = self.propose().data["id"]

        self.assertEqual(
            ItineraryProposal.objects.get(id=first).status, "superseded"
        )
        current = self.client.get(self.url).data["proposal"]
        self.assertEqual(current["id"], second)

    def test_get_without_pending_proposal(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["proposal"])


class ProposalValidationTests(ReplanTestCase):
    def test_requires_request_or_places(self):
        response = self.propose({"request": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("request", response.data)

    def test_request_limit(self):
        response = self.propose({"request": "a" * 501})

        self.assertEqual(response.status_code, 400)
        self.assertIn("request", response.data)

    def test_rejects_places_of_other_people(self):
        other = self.make_user("outra")
        place = SavedPlace.objects.create(owner=other, name="Lugar dela")

        for ids in ([place.id], [999999]):
            response = self.propose({"request": "x", "place_ids": ids})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["place_ids"], ["Lugar não encontrado."])

    def test_rejects_days_of_other_trips(self):
        other_trip = make_trip(self.owner)

        response = self.propose({
            "request": "x",
            "day_ids": [other_trip.days.first().id],
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("day_ids", response.data)

    def test_requires_destination(self):
        self.trip.destination = ""
        self.trip.save()

        response = self.propose()

        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.data)

    @patch(GENERATE_JSON)
    def test_invalid_ai_response_saves_nothing(self, generate_json):
        bad_responses = [
            fake_proposal(day_numbers=(1, 2)),  # falta o dia 3
            fake_proposal(days="não é lista"),
            {
                **fake_proposal(),
                "days": [
                    {"day_number": n, "title": "x", "activities": [{"title": ""}]}
                    for n in (1, 2, 3)
                ],
            },
            fake_proposal(estimates=None),
        ]

        for bad in bad_responses:
            generate_json.return_value = bad
            response = self.propose()
            self.assertEqual(response.status_code, 502)

        self.assertFalse(ItineraryProposal.objects.exists())

    @patch(GENERATE_JSON)
    def test_ai_failure_keeps_previous_proposal(self, generate_json):
        generate_json.return_value = fake_proposal()
        first = self.propose().data["id"]

        generate_json.side_effect = GeminiUnavailableError()
        response = self.propose()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(ItineraryProposal.objects.get(id=first).status, "pending")


class ApplyProposalTests(ReplanTestCase):
    def create(self, generate_json, **kwargs):
        generate_json.return_value = fake_proposal(**kwargs)
        return self.propose().data["id"]

    def apply(self, proposal_id):
        return self.client.post(f"{self.url}{proposal_id}/apply/")

    @patch(GENERATE_JSON)
    def test_apply_replaces_proposed_days(self, generate_json):
        proposal_id = self.create(generate_json)

        response = self.apply(proposal_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["proposal"]["status"], "applied")
        self.assertFalse(response.data["proposal"]["can_apply"])

        trip = response.data["trip"]
        self.assertEqual(trip["ai_summary"], "Lisboa com um dia em Sintra.")
        self.assertEqual(trip["cost_estimate"]["total"], "32000.00")
        day = trip["days"][1]
        self.assertEqual(day["title"], "Dia 2 ajustado")
        self.assertEqual(
            [a["title"] for a in day["activities"]],
            ["Café na Pastelaria", "Palácio da Pena"],
        )
        self.assertEqual(day["activities"][1]["start_time"], "10:30:00")
        self.assertEqual(day["activities"][1]["estimated_cost"], "20.00")
        self.assertEqual(day["activities"][1]["latitude"], "38.787600")
        self.assertEqual([a["order"] for a in day["activities"]], [1, 2])

    @patch(GENERATE_JSON)
    def test_apply_keeps_days_outside_proposal(self, generate_json):
        generate_json.return_value = fake_proposal(day_numbers=(2,))
        proposal_id = self.propose(
            {"request": "x", "day_ids": [self.days[1].id]}
        ).data["id"]

        self.apply(proposal_id)

        self.assertEqual(
            self.titles(self.days[0]),
            ["Mosteiro dos Jerónimos", "Museu do Azulejo"],
        )
        self.assertEqual(
            self.titles(self.days[1]), ["Café na Pastelaria", "Palácio da Pena"]
        )

    @patch(GENERATE_JSON)
    def test_cannot_apply_after_itinerary_changed(self, generate_json):
        proposal_id = self.create(generate_json)
        activity = self.days[0].activities.first()
        self.client.patch(
            f"/api/trips/{self.trip.id}/activities/{activity.id}/",
            {"title": "Outro passeio"},
            format="json",
        )

        detail = self.client.get(f"{self.url}{proposal_id}/").data
        self.assertTrue(detail["is_outdated"])
        self.assertFalse(detail["can_apply"])

        response = self.apply(proposal_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.titles(self.days[1])[0], "Mosteiro dos Jerónimos")

    @patch(GENERATE_JSON)
    def test_cannot_apply_twice_or_after_discard(self, generate_json):
        proposal_id = self.create(generate_json)
        self.apply(proposal_id)

        self.assertEqual(self.apply(proposal_id).status_code, 409)

        other_id = self.create(generate_json)
        self.client.post(f"{self.url}{other_id}/discard/")
        self.assertEqual(self.apply(other_id).status_code, 409)

    @patch(GENERATE_JSON)
    def test_superseded_proposal_cannot_be_applied(self, generate_json):
        first = self.create(generate_json)
        self.create(generate_json)

        self.assertEqual(self.apply(first).status_code, 409)

    @patch(GENERATE_JSON)
    def test_discard_keeps_itinerary(self, generate_json):
        proposal_id = self.create(generate_json)

        response = self.client.post(f"{self.url}{proposal_id}/discard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "discarded")
        self.assertEqual(response.data["decided_by"]["id"], self.owner.id)
        self.assertEqual(
            self.titles(self.days[1]),
            ["Mosteiro dos Jerónimos", "Museu do Azulejo"],
        )
        self.assertIsNone(self.client.get(self.url).data["proposal"])

    @patch(GENERATE_JSON)
    def test_proposal_of_other_trip_is_404(self, generate_json):
        proposal_id = self.create(generate_json)
        other_trip = make_trip(self.owner)

        response = self.client.post(
            f"/api/trips/{other_trip.id}/proposals/{proposal_id}/apply/"
        )

        self.assertEqual(response.status_code, 404)


class ProposalPermissionTests(ReplanTestCase):
    @patch(GENERATE_JSON)
    def test_participant_can_propose_but_not_apply(self, generate_json):
        generate_json.return_value = fake_proposal()
        member = self.add_member()
        self.authenticate(member)

        response = self.propose()

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["can_apply"])
        self.assertTrue(response.data["can_discard"])
        self.assertEqual(response.data["created_by"]["id"], member.id)

        apply = self.client.post(f"{self.url}{response.data['id']}/apply/")
        self.assertEqual(apply.status_code, 404)
        self.assertEqual(
            self.titles(self.days[1])[0], "Mosteiro dos Jerónimos"
        )

        # A organizadora vê e pode aplicar a proposta da integrante.
        self.authenticate(self.owner)
        pending = self.client.get(self.url).data["proposal"]
        self.assertTrue(pending["can_apply"])
        self.assertEqual(
            self.client.post(f"{self.url}{pending['id']}/apply/").status_code, 200
        )

    @patch(GENERATE_JSON)
    def test_participant_cannot_discard_owner_proposal(self, generate_json):
        generate_json.return_value = fake_proposal()
        proposal_id = self.propose().data["id"]
        member = self.add_member()
        self.authenticate(member)

        detail = self.client.get(f"{self.url}{proposal_id}/").data
        self.assertFalse(detail["can_discard"])

        response = self.client.post(f"{self.url}{proposal_id}/discard/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            ItineraryProposal.objects.get(id=proposal_id).status, "pending"
        )

    @patch(GENERATE_JSON)
    def test_participant_uses_only_own_places(self, generate_json):
        generate_json.return_value = fake_proposal()
        owner_place = SavedPlace.objects.create(owner=self.owner, name="Da Luana")
        member = self.add_member()
        member_place = SavedPlace.objects.create(owner=member, name="Da amiga")
        self.authenticate(member)

        denied = self.propose({"request": "x", "place_ids": [owner_place.id]})
        allowed = self.propose({"request": "x", "place_ids": [member_place.id]})

        self.assertEqual(denied.status_code, 400)
        self.assertEqual(allowed.status_code, 201)
        self.assertIn("Da amiga", generate_json.call_args.args[0])

    @patch(GENERATE_JSON)
    def test_outsiders_and_pending_invites_get_404(self, generate_json):
        generate_json.return_value = fake_proposal()
        proposal_id = self.propose().data["id"]
        generate_json.reset_mock()

        stranger = self.make_user("estranha")
        guest = self.add_member("convidada", accepted=False)

        for user in (stranger, guest):
            self.authenticate(user)
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertEqual(self.propose().status_code, 404)
            self.assertEqual(
                self.client.get(f"{self.url}{proposal_id}/").status_code, 404
            )
            self.assertEqual(
                self.client.post(f"{self.url}{proposal_id}/apply/").status_code,
                404,
            )
            self.assertEqual(
                self.client.post(f"{self.url}{proposal_id}/discard/").status_code,
                404,
            )

        generate_json.assert_not_called()
        self.assertEqual(
            ItineraryProposal.objects.get(id=proposal_id).status, "pending"
        )

    def test_requires_authentication(self):
        self.client.credentials()

        self.assertEqual(self.client.get(self.url).status_code, 401)


class AiAnswerQualityTests(ReplanTestCase):
    """Correções feitas no backend quando a IA não segue todas as regras."""

    def day(self, number, *activities):
        return {"day_number": number, "title": f"Dia {number}",
                "activities": list(activities)}

    @patch(GENERATE_JSON)
    def test_removes_activity_repeated_from_unchanged_day(self, generate_json):
        generate_json.return_value = fake_proposal(days=[self.day(
            2,
            fake_activity("Mosteiro dos Jerónimos", "09:00"),
            fake_activity("Palácio da Pena", "11:00"),
        )])

        response = self.propose({"request": "Sintra", "day_ids": [self.days[1].id]})

        self.assertEqual(
            [a["title"] for a in response.data["days"][0]["proposed"]],
            ["Palácio da Pena"],
        )

    @patch(GENERATE_JSON)
    def test_removes_repetitions_inside_the_proposal(self, generate_json):
        generate_json.return_value = fake_proposal(days=[
            self.day(1, fake_activity("Café do hotel", "08:00", "gastronomy"),
                     fake_activity("Torre de Belém", "10:00")),
            self.day(2, fake_activity("Café do hotel", "08:00", "gastronomy"),
                     fake_activity("torre de belem", "10:00"),
                     fake_activity("Palácio da Pena", "11:00"),
                     fake_activity("Palácio da Pena", "15:00")),
            self.day(3, fake_activity("Oceanário", "10:00")),
        ])

        days = self.propose().data["days"]

        # Refeições podem repetir; passeios não.
        self.assertEqual(
            [a["title"] for a in days[0]["proposed"]],
            ["Café do hotel", "Torre de Belém"],
        )
        self.assertEqual(
            [a["title"] for a in days[1]["proposed"]],
            ["Café do hotel", "Palácio da Pena"],
        )

    @patch(GENERATE_JSON)
    def test_day_with_only_repetitions_is_rejected(self, generate_json):
        generate_json.return_value = fake_proposal(days=[self.day(
            2, fake_activity("Mosteiro dos Jerónimos", "09:00"),
        )])

        response = self.propose({"request": "x", "day_ids": [self.days[1].id]})

        self.assertEqual(response.status_code, 502)
        self.assertFalse(ItineraryProposal.objects.exists())

    def closed_poll(self, title, category, label):
        TripPoll.objects.create(
            trip=self.trip, title=title, category=category, status="closed",
            closed_at=timezone.now(), decision={"label": label, "reason": ""},
        )

    @patch(GENERATE_JSON)
    def test_warns_about_missing_places_and_decisions(self, generate_json):
        generate_json.return_value = fake_proposal()
        place = SavedPlace.objects.create(owner=self.owner, name="LX Factory",
                                          city="Lisboa", category="shopping")
        self.closed_poll("Jantar de sexta", "restaurant", "Cervejaria Ramiro")
        self.closed_poll("Destino", "destination", "Lisboa")

        response = self.propose({"request": "Mais leve", "place_ids": [place.id]})

        # A decisão de destino não vira atividade, então não gera aviso.
        self.assertEqual(response.data["warnings"], [
            "LX Factory não entrou na proposta.",
            'A decisão do grupo "Jantar de sexta" (Cervejaria Ramiro) não '
            "aparece no roteiro.",
        ])

    @patch(GENERATE_JSON)
    def test_no_warnings_when_everything_is_included(self, generate_json):
        place = SavedPlace.objects.create(owner=self.owner, name="Palácio da Pena",
                                          city="Sintra", category="culture")
        # A decisão já está em um dia que não muda.
        self.closed_poll("Passeio", "activity", "Museu do Azulejo")
        generate_json.return_value = fake_proposal(day_numbers=(2,))

        response = self.propose({"place_ids": [place.id],
                                 "day_ids": [self.days[1].id]})

        self.assertEqual(response.data["warnings"], [])

    @patch(GENERATE_JSON)
    def test_prompt_lets_request_set_pace_and_forbids_unknown_places(self, generate_json):
        generate_json.return_value = fake_proposal()

        self.propose({"request": "No máximo 2 atividades por dia."})

        prompt = generate_json.call_args.args[0]
        self.assertIn("quantas atividades quer ou a partir de que horário, siga o pedido", prompt)
        self.assertIn("Inclua apenas lugares reais", prompt)
        self.assertIn("cada lugar pedido e cada decisão do grupo", prompt)


class CompareDayTests(APITestCase):
    def test_ignores_case_and_accents(self):
        result = compare_day(
            ["Museu do Azulejo", "Jantar"],
            ["museu do azulejo", "Palácio da Pena"],
        )

        self.assertEqual(result["kept"], ["museu do azulejo"])
        self.assertEqual(result["added"], ["Palácio da Pena"])
        self.assertEqual(result["removed"], ["Jantar"])


class ParseProposalTests(APITestCase):
    def test_invalid_structure_raises(self):
        from .replanning import parse_proposal

        owner = User.objects.create_user(
            username="x", email="x@exemplo.com", password="senha-forte-123"
        )
        trip = make_trip(owner)
        with self.assertRaises(GeminiInvalidResponseError):
            parse_proposal(["lista"], trip, list(trip.days.all()))
