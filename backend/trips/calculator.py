"""
Calculadora de custo e duração da viagem (aba "Orçamento").

Dois modos:
- duration: quanto custa a viagem para uma quantidade de dias;
- budget: quantos dias cabem em um orçamento.

Fluxo:
1. get_cost_rates() pede à IA apenas os valores de referência do destino
   (passagem de ida e volta, diária de hospedagem e gastos diários por
   pessoa). Esses valores dependem do destino, da origem, do estilo, do
   transporte, do número de viajantes e da época, mas não da duração nem do
   orçamento. Por isso ficam guardados em Trip.cost_rates e só são pedidos
   de novo quando algum desses dados muda (ou com refresh=True).
2. estimate_for_duration() e duration_for_budget() fazem as contas no
   backend, de forma previsível, a partir desses valores.
"""

import hashlib
import json
from decimal import ROUND_FLOOR, Decimal

from django.utils import timezone

from core.gemini import GeminiInvalidResponseError, generate_json

from .itinerary import SYSTEM_INSTRUCTION, _decimal, _label, _text
from .models import Trip
from .serializers import MAX_TRIP_DAYS


CENTS = Decimal("0.01")
ZERO = Decimal("0.00")

# Valores que a IA precisa informar, todos na moeda da viagem.
RATE_FIELDS = [
    "transport_round_trip",
    "lodging_per_night",
    "food_per_person_per_day",
    "activities_per_person_per_day",
    "local_transport_per_person_per_day",
]

# Sem hospedagem ou sem alimentação, a estimativa não faz sentido.
REQUIRED_POSITIVE_RATES = ["lodging_per_night", "food_per_person_per_day"]

CATEGORIES = ["transport", "lodging", "food", "activities"]


RATES_SCHEMA = {
    "type": "object",
    "properties": {
        "transport_round_trip": {
            "type": "number",
            "description": "Ida e volta a partir da origem, total do grupo",
        },
        "lodging_per_night": {
            "type": "number",
            "description": "Uma noite de hospedagem para todo o grupo",
        },
        "food_per_person_per_day": {"type": "number"},
        "activities_per_person_per_day": {"type": "number"},
        "local_transport_per_person_per_day": {"type": "number"},
        "notes": {"type": "string"},
    },
    "required": RATE_FIELDS,
}


# ---------------------------------------------------------------------------
# Valores de referência (IA)
# ---------------------------------------------------------------------------


def _rates_inputs(trip, style):
    """Dados da viagem que influenciam os valores de referência."""
    return {
        "destination": trip.destination.strip().lower(),
        "origin": trip.origin.strip().lower(),
        "travelers_count": trip.travelers_count,
        "currency": trip.currency,
        "style": style or "",
        "transport": trip.transport or "",
        "month": trip.start_date.month,
    }


def rates_fingerprint(trip, style):
    raw = json.dumps(_rates_inputs(trip, style), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _style_label(style):
    return dict(Trip.Style.choices).get(style, "não informado")


def _itinerary_reference(trip):
    """Estimativa do roteiro já gerado, para a IA manter a coerência."""
    estimate = trip.cost_estimate or {}
    if not estimate.get("total"):
        return ""
    return (
        "\nO roteiro atual desta viagem foi estimado assim (total do grupo, "
        f"{trip.duration_days} dias): transporte {estimate.get('transport')}, "
        f"hospedagem {estimate.get('lodging')}, alimentação "
        f"{estimate.get('food')}, atividades {estimate.get('activities')}. "
        "Mantenha os valores coerentes com essa estimativa.\n"
    )


def build_rates_prompt(trip, style):
    return (
        "Estime os custos de referência de uma viagem.\n\n"
        "Dados da viagem:\n"
        f"- Origem: {trip.origin}\n"
        f"- Destino: {trip.destination}\n"
        f"- Mês da viagem: {trip.start_date:%m/%Y}\n"
        f"- Viajantes: {trip.travelers_count}\n"
        f"- Estilo: {_style_label(style)}\n"
        f"- Transporte principal: {_label(trip, 'transport')}\n"
        f"- Moeda: {trip.currency}\n"
        f"{_itinerary_reference(trip)}"
        "\nComo montar a resposta (todos os valores na moeda informada, "
        "como números, sem símbolo):\n"
        "- transport_round_trip: custo total de ida e volta entre a origem e "
        "o destino para TODO o grupo, no transporte principal informado. Use "
        "0 apenas se origem e destino forem a mesma cidade.\n"
        "- lodging_per_night: preço de uma noite de hospedagem para TODO o "
        "grupo (considere quantos quartos são necessários), compatível com o "
        "estilo.\n"
        "- food_per_person_per_day: café da manhã, almoço e jantar de UMA "
        "pessoa em um dia, compatível com o estilo.\n"
        "- activities_per_person_per_day: média diária de ingressos e "
        "passeios de UMA pessoa.\n"
        "- local_transport_per_person_per_day: metrô, ônibus, táxi ou "
        "aplicativo dentro do destino para UMA pessoa em um dia.\n"
        "- notes: uma frase sobre as suposições usadas (ex.: alta temporada)."
    )


def parse_rates(data):
    """Valida os valores da IA. Levanta GeminiInvalidResponseError se faltar algo."""
    if not isinstance(data, dict):
        raise GeminiInvalidResponseError()

    rates = {}
    for field in RATE_FIELDS:
        value = _decimal(data.get(field))
        if value is None:
            raise GeminiInvalidResponseError()
        rates[field] = value

    if any(rates[field] <= 0 for field in REQUIRED_POSITIVE_RATES):
        raise GeminiInvalidResponseError()

    return {
        **{field: str(value) for field, value in rates.items()},
        "notes": _text(data.get("notes"), 500),
    }


def get_cost_rates(trip, style, refresh=False):
    """
    Devolve os valores de referência, usando os guardados na viagem quando
    os dados que os influenciam não mudaram.
    """
    fingerprint = rates_fingerprint(trip, style)
    saved = trip.cost_rates or {}

    if not refresh and saved.get("fingerprint") == fingerprint:
        return saved

    data = generate_json(
        build_rates_prompt(trip, style),
        system_instruction=SYSTEM_INSTRUCTION,
        schema=RATES_SCHEMA,
        required_keys=RATE_FIELDS,
        temperature=0.2,
    )

    trip.cost_rates = {
        "fingerprint": fingerprint,
        "style": style or "",
        "generated_at": timezone.now().isoformat(),
        "rates": parse_rates(data),
    }
    trip.save(update_fields=["cost_rates", "updated_at"])
    return trip.cost_rates


# ---------------------------------------------------------------------------
# Contas
# ---------------------------------------------------------------------------


def _rates_as_decimal(rates):
    return {field: Decimal(rates[field]) for field in RATE_FIELDS}


def _daily_group_cost(rates, travelers):
    per_person = (
        rates["food_per_person_per_day"]
        + rates["activities_per_person_per_day"]
        + rates["local_transport_per_person_per_day"]
    )
    return per_person * travelers


def breakdown(rates, travelers, days):
    """Custo por categoria para o grupo todo em uma viagem de `days` dias."""
    nights = max(days - 1, 0)
    categories = {
        "transport": rates["transport_round_trip"]
        + rates["local_transport_per_person_per_day"] * travelers * days,
        "lodging": rates["lodging_per_night"] * nights,
        "food": rates["food_per_person_per_day"] * travelers * days,
        "activities": rates["activities_per_person_per_day"] * travelers * days,
    }
    categories = {key: value.quantize(CENTS) for key, value in categories.items()}
    total = sum(categories.values(), ZERO)
    return nights, categories, total


def max_days_for_budget(rates, travelers, budget):
    """
    Maior quantidade de dias (até MAX_TRIP_DAYS) cujo custo cabe no
    orçamento. Devolve 0 quando nem um dia cabe.

    custo(d) = passagem + hospedagem * (d - 1) + gasto_diário_do_grupo * d
    """
    per_extra_day = rates["lodging_per_night"] + _daily_group_cost(rates, travelers)
    available = budget - rates["transport_round_trip"] + rates["lodging_per_night"]
    days = int((available / per_extra_day).to_integral_value(rounding=ROUND_FLOOR))
    days = max(0, min(days, MAX_TRIP_DAYS))

    # Garante que os arredondamentos em centavos não estourem o orçamento.
    while days > 0 and breakdown(rates, travelers, days)[2] > budget:
        days -= 1
    return days


def _result(trip, mode, style, saved_rates, days, budget):
    rates = _rates_as_decimal(saved_rates["rates"])
    travelers = trip.travelers_count
    nights, categories, total = breakdown(rates, travelers, days) if days else (
        0,
        {key: ZERO for key in CATEGORIES},
        ZERO,
    )

    reference_budget = budget if budget is not None else trip.budget
    minimum_cost = breakdown(rates, travelers, 1)[2]

    if reference_budget is None:
        within_budget = remaining = None
    elif days:
        within_budget = total <= reference_budget
        remaining = reference_budget - total
    else:
        # Nem um dia cabe: o saldo negativo mostra quanto falta para o mínimo.
        within_budget = False
        remaining = reference_budget - minimum_cost

    return {
        "mode": mode,
        "currency": trip.currency,
        "travelers_count": travelers,
        "style": style or "",
        "days": days,
        "nights": nights,
        "budget": str(reference_budget) if reference_budget is not None else None,
        "categories": {key: str(value) for key, value in categories.items()},
        "total": str(total),
        "per_person": str((total / travelers).quantize(CENTS)),
        "per_day": str((total / days).quantize(CENTS)) if days else None,
        "within_budget": within_budget,
        "remaining": (
            str(remaining.quantize(CENTS)) if remaining is not None else None
        ),
        "minimum_cost": str(minimum_cost),
        "max_days_reached": mode == "budget" and days == MAX_TRIP_DAYS,
        "rates": saved_rates["rates"],
        "rates_generated_at": saved_rates["generated_at"],
    }


def estimate_for_duration(trip, days, style, refresh=False):
    saved_rates = get_cost_rates(trip, style, refresh=refresh)
    return _result(trip, "duration", style, saved_rates, days, budget=None)


def duration_for_budget(trip, budget, style, refresh=False):
    saved_rates = get_cost_rates(trip, style, refresh=refresh)
    rates = _rates_as_decimal(saved_rates["rates"])
    days = max_days_for_budget(rates, trip.travelers_count, budget)
    return _result(trip, "budget", style, saved_rates, days, budget=budget)
