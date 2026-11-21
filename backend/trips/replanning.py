"""
Replanejamento do roteiro e inclusão de sugestões (issue S2-15).

Fluxo:
1. create_proposal() monta o pedido com o roteiro atual, o pedido livre, os
   lugares que devem entrar e as decisões das votações encerradas do grupo.
2. A IA devolve só os dias que podem mudar, no mesmo formato da geração de
   roteiro. A resposta é validada por parse_proposal().
3. A proposta fica guardada em ItineraryProposal. O roteiro atual não muda.
4. apply_proposal() troca as atividades dos dias propostos, de uma vez só,
   desde que o roteiro não tenha mudado depois da proposta.
"""

import hashlib
import json
import unicodedata
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from core.gemini import GeminiInvalidResponseError, generate_json

from .itinerary import (
    ACTIVITY_SCHEMA,
    ACTIVITIES_PER_PACE,
    MAX_ACTIVITIES_PER_DAY,
    SYSTEM_INSTRUCTION,
    WEEKDAYS,
    _parse_activity,
    _parse_estimates,
    _saved_places_text,
    _text,
    _time,
    _trip_profile_text,
    _user_request,
)
from .models import Activity, ItineraryProposal


MAX_CHANGES = 8
MAX_DECISIONS_IN_PROMPT = 20

# Campos de Activity guardados na proposta.
ACTIVITY_FIELDS = [
    "title",
    "description",
    "category",
    "start_time",
    "end_time",
    "duration_minutes",
    "location_name",
    "address",
    "latitude",
    "longitude",
    "estimated_cost",
    "cost_type",
    "notes",
]


class ProposalOutdatedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "O roteiro mudou depois que esta proposta foi gerada. "
        "Gere uma nova proposta."
    )
    default_code = "proposal_outdated"


class ProposalClosedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Esta proposta já foi aplicada, descartada ou substituída."
    default_code = "proposal_closed"


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "changes": {"type": "array", "items": {"type": "string"}},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day_number": {"type": "integer"},
                    "title": {"type": "string"},
                    "activities": {"type": "array", "items": ACTIVITY_SCHEMA},
                },
                "required": ["day_number", "title", "activities"],
            },
        },
        "estimates": {
            "type": "object",
            "properties": {
                "transport": {"type": "number"},
                "lodging": {"type": "number"},
                "food": {"type": "number"},
                "activities": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["transport", "lodging", "food", "activities"],
        },
    },
    "required": ["summary", "changes", "days", "estimates"],
}


# ---------------------------------------------------------------------------
# Versão do roteiro
# ---------------------------------------------------------------------------


def itinerary_fingerprint(trip):
    """Muda sempre que um dia ou atividade é criado, editado ou removido."""
    days = []
    for day in trip.days.order_by("date").prefetch_related("activities"):
        days.append([
            day.id,
            day.date.isoformat(),
            day.title,
            sorted(
                [activity.id, activity.updated_at.isoformat()]
                for activity in day.activities.all()
            ),
        ])
    raw = json.dumps(days)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _money(value):
    return f"{value:.2f}".rstrip("0").rstrip(".") if value else "0"


def _activity_line(activity):
    when = f"{activity.start_time:%H:%M}" if activity.start_time else "sem horário"
    line = f"  - {when} · {activity.title} [{activity.category}]"
    if activity.location_name and activity.location_name != activity.title:
        line += f" em {activity.location_name}"
    cost = activity.estimated_cost or Decimal("0")
    line += f" · custo {_money(cost)} ({activity.cost_type})"
    return line


def _current_itinerary_text(trip, editable_ids):
    lines = []
    for day in trip.days.order_by("date").prefetch_related("activities"):
        mark = "PODE MUDAR" if day.id in editable_ids else "NÃO MUDAR"
        header = (
            f"- Dia {day.day_number} ({WEEKDAYS[day.date.weekday()]}, "
            f"{day.date:%d/%m/%Y}) [{mark}]"
        )
        if day.title:
            header += f": {day.title}"
        lines.append(header)

        activities = list(day.activities.all())
        if activities:
            lines.extend(_activity_line(activity) for activity in activities)
        else:
            lines.append("  (sem atividades)")
    return "\n".join(lines)


def _requested_places_text(places):
    lines = []
    for place in places:
        where = ", ".join(part for part in [place.city, place.country] if part)
        line = f"- {place.name} [{place.category}]"
        if where:
            line += f" ({where})"
        if place.address:
            line += f", endereço: {place.address}"
        if place.notes:
            line += f": {place.notes}"
        lines.append(line)
    return "\n".join(lines)


def group_decisions(trip):
    """Votações encerradas da viagem, com a opção escolhida."""
    polls = trip.polls.filter(status="closed").order_by("closed_at")
    decisions = []
    for poll in polls[:MAX_DECISIONS_IN_PROMPT]:
        decision = poll.decision or {}
        label = decision.get("label")
        if not label:
            continue
        decisions.append({
            "category": poll.category,
            "title": poll.title,
            "choice": label,
            "reason": decision.get("reason", ""),
        })
    return decisions


def _decisions_text(decisions):
    labels = {
        "destination": "Destino",
        "restaurant": "Restaurante",
        "activity": "Atividade",
    }
    lines = []
    for item in decisions:
        line = (
            f"- {labels.get(item['category'], item['category'])} · "
            f"\"{item['title']}\": escolhido {item['choice']}"
        )
        if item["reason"]:
            line += f" (motivo: {item['reason']})"
        lines.append(line)
    return "\n".join(lines)


def build_replan_prompt(trip, editable_days, request, places, decisions):
    editable_ids = {day.id for day in editable_days}
    numbers = ", ".join(str(day.day_number) for day in editable_days)
    per_day = ACTIVITIES_PER_PACE.get(trip.pace, "3 a 5")

    places_text = _requested_places_text(places)
    places_block = (
        "\nLugares que DEVEM entrar nos dias que podem mudar (cada um uma "
        "vez, em um dia e horário que façam sentido; use a categoria "
        f"indicada):\n{places_text}\n"
        if places_text
        else ""
    )

    saved = _saved_places_text(trip)
    saved_block = (
        "\nOutros lugares salvos para esta viagem (inclua apenas se combinar "
        f"com o pedido):\n{saved}\n"
        if saved
        else ""
    )

    decisions_text = _decisions_text(decisions)
    decisions_block = (
        "\nDecisões já tomadas pelo grupo em votação (respeite sempre; "
        "restaurantes e atividades escolhidos devem continuar ou entrar no "
        f"roteiro):\n{decisions_text}\n"
        if decisions_text
        else ""
    )

    return (
        f"Ajuste o roteiro de viagem para {trip.destination}.\n\n"
        f"Dados da viagem:\n{_trip_profile_text(trip)}"
        f"\nRoteiro atual:\n{_current_itinerary_text(trip, editable_ids)}\n"
        f"{_user_request(request)}"
        f"{places_block}"
        f"{decisions_block}"
        f"{saved_block}"
        "\nComo montar a resposta:\n"
        f"- Em days, devolva exatamente os dias {numbers} (os marcados com "
        "PODE MUDAR), cada um com a lista COMPLETA de atividades como devem "
        "ficar. Não devolva os outros dias.\n"
        "- Mude só o necessário para atender o pedido, os lugares e as "
        "decisões. Mantenha as atividades atuais que não conflitam, com os "
        "mesmos títulos, horários e custos.\n"
        "- Não repita no dia uma atividade que já aparece em outro dia.\n"
        f"- Cada dia deve ter de {per_day} atividades (no máximo "
        f"{MAX_ACTIVITIES_PER_DAY}), em ordem de horário, com almoço e "
        "jantar na categoria gastronomy. Se o pedido do viajante disser "
        "quantas atividades quer ou a partir de que horário, siga o pedido.\n"
        "- Inclua apenas lugares reais. Se o pedido citar um lugar que você "
        "não conhece, não o inclua e diga isso em changes.\n"
        "- estimated_cost e cost_type seguem as mesmas regras do roteiro "
        "atual (per_person ou total). Use 0 para atividades gratuitas.\n"
        "- Em changes, liste de 1 a 5 frases curtas sobre o que mudou e por "
        "quê (ex.: \"Dia 2: Sintra entrou no lugar do museu, como pedido\"), "
        "citando em que dia ficou cada lugar pedido e cada decisão do grupo.\n"
        "- summary é um resumo curto (até 2 frases) do roteiro ajustado.\n"
        "- Em estimates, informe o custo total do grupo para a viagem toda "
        "depois do ajuste, por categoria: transport, lodging, food e "
        "activities."
    )


# ---------------------------------------------------------------------------
# Validação da resposta
# ---------------------------------------------------------------------------


def _activity_to_json(activity):
    data = {}
    for field in ACTIVITY_FIELDS:
        value = activity[field]
        if value is None:
            data[field] = None
        elif field in {"start_time", "end_time"}:
            data[field] = value.strftime("%H:%M:%S")
        elif isinstance(value, Decimal):
            data[field] = str(value)
        else:
            data[field] = value
    return data


# Refeições podem se repetir (ex.: café da manhã no hotel todos os dias).
REPEATABLE_CATEGORIES = {Activity.Category.GASTRONOMY}


def _remove_repeated(days, trip, editable_ids):
    """
    Tira das propostas as atividades que já aparecem em outro dia (dos que
    não mudam ou de um dia anterior da própria proposta). A IA às vezes
    repete um passeio mesmo com a regra no prompt.
    """
    seen = {
        _key(activity.title)
        for activity in Activity.objects.filter(day__trip=trip)
        .exclude(day_id__in=editable_ids)
        .exclude(category__in=REPEATABLE_CATEGORIES)
    }
    for day in days:
        kept, in_day = [], set()
        for activity in day["activities"]:
            key = _key(activity["title"])
            repeated = key in in_day or (
                activity["category"] not in REPEATABLE_CATEGORIES and key in seen
            )
            if repeated:
                continue
            in_day.add(key)
            kept.append(activity)
        day["activities"] = kept
        seen |= {
            _key(activity["title"])
            for activity in kept
            if activity["category"] not in REPEATABLE_CATEGORIES
        }


def _mentioned(name, titles):
    key = _key(name)
    return bool(key) and any(key in title for title in titles)


def proposal_warnings(days, trip, editable_ids, places, decisions):
    """Lugares pedidos e decisões do grupo que não entraram no roteiro."""
    titles = [
        _key(f"{activity['title']} {activity.get('location_name') or ''}")
        for day in days
        for activity in day["activities"]
    ]
    titles += [
        _key(f"{activity.title} {activity.location_name}")
        for activity in Activity.objects.filter(day__trip=trip).exclude(
            day_id__in=editable_ids
        )
    ]

    warnings = [
        f"{place.name} não entrou na proposta."
        for place in places
        if not _mentioned(place.name, titles)
    ]
    warnings += [
        f"A decisão do grupo \"{item['title']}\" ({item['choice']}) não "
        "aparece no roteiro."
        for item in decisions
        if item["category"] in {"restaurant", "activity"}
        and not _mentioned(item["choice"], titles)
    ]
    return warnings


def parse_proposal(data, trip, editable_days, places=(), decisions=()):
    """Valida a resposta e devolve a proposta pronta para guardar em JSON."""
    if not isinstance(data, dict) or not isinstance(data.get("days"), list):
        raise GeminiInvalidResponseError()

    raw_days = {}
    for raw_day in data["days"]:
        if not isinstance(raw_day, dict):
            continue
        number = raw_day.get("day_number")
        if isinstance(number, int) and not isinstance(number, bool):
            raw_days.setdefault(number, raw_day)

    days = []
    for day in editable_days:
        raw_day = raw_days.get(day.day_number)
        if raw_day is None or not isinstance(raw_day.get("activities"), list):
            raise GeminiInvalidResponseError()

        activities = [
            activity
            for activity in map(_parse_activity, raw_day["activities"])
            if activity is not None
        ][:MAX_ACTIVITIES_PER_DAY]
        activities.sort(
            key=lambda item: (item["start_time"] is None, item["start_time"] or "")
        )

        days.append({
            "day_id": day.id,
            "day_number": day.day_number,
            "title": _text(raw_day.get("title"), 120) or day.title,
            "activities": [_activity_to_json(item) for item in activities],
        })

    editable_ids = {day.id for day in editable_days}
    _remove_repeated(days, trip, editable_ids)

    if not any(day["activities"] for day in days):
        raise GeminiInvalidResponseError()

    raw_changes = data.get("changes") if isinstance(data.get("changes"), list) else []
    changes = [text for text in (_text(item, 300) for item in raw_changes) if text]

    return {
        "summary": _text(data.get("summary"), 1000),
        "changes": changes[:MAX_CHANGES],
        "days": days,
        "estimates": _parse_estimates(data.get("estimates"), trip),
        "warnings": proposal_warnings(days, trip, editable_ids, places, decisions),
    }


# ---------------------------------------------------------------------------
# Criar, aplicar e descartar
# ---------------------------------------------------------------------------


def create_proposal(trip, user, request="", places=(), editable_days=None):
    """
    Gera uma proposta e a guarda como pendente, substituindo a anterior.
    Se a IA falhar, nada é salvo e a proposta anterior continua valendo.
    """
    all_days = list(trip.days.order_by("date"))
    if editable_days is None:
        editable_days = all_days
    else:
        editable_ids = {day.id for day in editable_days}
        editable_days = [day for day in all_days if day.id in editable_ids]

    places = list(places)
    decisions = group_decisions(trip)
    base = itinerary_fingerprint(trip)

    data = generate_json(
        build_replan_prompt(trip, editable_days, request, places, decisions),
        system_instruction=SYSTEM_INSTRUCTION,
        schema=PROPOSAL_SCHEMA,
        required_keys=["days", "estimates"],
        temperature=0.5,
    )
    proposal = parse_proposal(data, trip, editable_days, places, decisions)
    proposal["decisions"] = decisions

    with transaction.atomic():
        trip.proposals.filter(status=ItineraryProposal.Status.PENDING).update(
            status=ItineraryProposal.Status.SUPERSEDED,
            decided_at=timezone.now(),
        )
        return ItineraryProposal.objects.create(
            trip=trip,
            created_by=user,
            request=request,
            place_ids=[place.id for place in places],
            day_ids=[day.id for day in editable_days],
            proposal=proposal,
            base_fingerprint=base,
        )


def _activity_from_json(data):
    fields = dict(data)
    for field in ("start_time", "end_time"):
        fields[field] = _time(fields[field]) if fields[field] else None
    for field in ("latitude", "longitude", "estimated_cost"):
        if fields[field] is not None:
            fields[field] = Decimal(fields[field])
    return fields


def _require_pending(proposal):
    if proposal.status != ItineraryProposal.Status.PENDING:
        raise ProposalClosedError()


def is_outdated(proposal):
    return itinerary_fingerprint(proposal.trip) != proposal.base_fingerprint


@transaction.atomic
def apply_proposal(proposal, user):
    proposal = ItineraryProposal.objects.select_for_update().get(pk=proposal.pk)
    _require_pending(proposal)

    trip = proposal.trip
    if is_outdated(proposal):
        raise ProposalOutdatedError()

    days = {day.id: day for day in trip.days.all()}

    for proposed in proposal.proposal["days"]:
        day = days[proposed["day_id"]]
        day.activities.all().delete()
        if proposed["title"] != day.title:
            day.title = proposed["title"]
            day.save(update_fields=["title", "updated_at"])
        Activity.objects.bulk_create([
            Activity(day=day, order=position, **_activity_from_json(activity))
            for position, activity in enumerate(proposed["activities"], start=1)
        ])

    if proposal.proposal.get("summary"):
        trip.ai_summary = proposal.proposal["summary"]
    trip.cost_estimate = proposal.proposal["estimates"]
    trip.save(update_fields=["ai_summary", "cost_estimate", "updated_at"])

    proposal.status = ItineraryProposal.Status.APPLIED
    proposal.decided_at = timezone.now()
    proposal.decided_by = user
    proposal.save(update_fields=["status", "decided_at", "decided_by"])
    return proposal


@transaction.atomic
def discard_proposal(proposal, user):
    proposal = ItineraryProposal.objects.select_for_update().get(pk=proposal.pk)
    _require_pending(proposal)

    proposal.status = ItineraryProposal.Status.DISCARDED
    proposal.decided_at = timezone.now()
    proposal.decided_by = user
    proposal.save(update_fields=["status", "decided_at", "decided_by"])
    return proposal


# ---------------------------------------------------------------------------
# Comparação com o roteiro atual
# ---------------------------------------------------------------------------


def _key(title):
    text = unicodedata.normalize("NFKD", title or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def compare_day(current_titles, proposed_titles):
    current = {_key(title): title for title in current_titles}
    proposed = {_key(title): title for title in proposed_titles}
    return {
        "added": [title for key, title in proposed.items() if key not in current],
        "removed": [title for key, title in current.items() if key not in proposed],
        "kept": [title for key, title in proposed.items() if key in current],
    }
