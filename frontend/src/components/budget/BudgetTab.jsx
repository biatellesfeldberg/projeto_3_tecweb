// Aba "Orçamento" da viagem (issue S2-20).
// Mostra os gastos estimados (total e por pessoa) e a calculadora de custo
// e duração. Contratos: docs/contratos-api.md, seções "cost_estimate" e
// "POST /api/trips/{id}/cost-calculator/".

import { useRef, useState } from "react";

import { Button, ButtonLink, Field } from "../ui";
import Feedback from "../Feedback";
import { useAuth } from "../../contexts/AuthContext";
import { calculateCosts } from "../../services/trips";
import { formatMoney } from "../../utils/itinerary";
import { pluralize } from "../../utils/places";
import { normalizeBudget, travelStyles } from "../../utils/tripForm";

import "./budget.css";

export const costCategories = [
  ["transport", "Transporte"],
  ["lodging", "Hospedagem"],
  ["food", "Alimentação"],
  ["activities", "Atividades"],
];

const rateLabels = [
  ["transport_round_trip", "Passagem de ida e volta (grupo)"],
  ["lodging_per_night", "Hospedagem por noite (grupo)"],
  ["food_per_person_per_day", "Alimentação por pessoa, por dia"],
  ["activities_per_person_per_day", "Atividades por pessoa, por dia"],
  [
    "local_transport_per_person_per_day",
    "Transporte local por pessoa, por dia",
  ],
];

const MAX_DAYS = 60;

function perPerson(value, travelers) {
  return Number(value) / Math.max(Number(travelers) || 1, 1);
}

function activitiesTotal(trip) {
  return (trip.days || []).reduce(
    (sum, day) =>
      sum +
      day.activities.reduce(
        (daySum, activity) => daySum + Number(activity.total_cost || 0),
        0,
      ),
    0,
  );
}

function StatTile({ label, value, detail, tone }) {
  return (
    <div className={`budget-stat ${tone ? `budget-stat--${tone}` : ""}`}>
      <p className="budget-stat-label">{label}</p>
      <p className="budget-stat-value">{value}</p>
      {detail && <p className="budget-stat-detail">{detail}</p>}
    </div>
  );
}

export function CategoryBreakdown({ categories, total, travelers, currency }) {
  const sum = Number(total) || 0;

  return (
    <ul className="budget-categories">
      {costCategories.map(([key, label]) => {
        const value = Number(categories?.[key] || 0);
        const share = sum > 0 ? Math.round((value / sum) * 100) : 0;

        return (
          <li key={key} className="budget-category">
            <div className="budget-category-row">
              <span className="budget-category-name">{label}</span>
              <span className="budget-category-value">
                {formatMoney(value, currency)}
                <span className="muted">
                  {" "}
                  · {formatMoney(perPerson(value, travelers), currency)} / pessoa
                </span>
              </span>
            </div>

            <div
              className="budget-bar"
              role="img"
              aria-label={`${label}: ${share}% do total`}
            >
              <span
                className={`budget-bar-fill budget-bar-fill--${key}`}
                style={{ width: `${share}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function BudgetStatus({ budget, total, currency, withinBudget }) {
  if (budget === null || budget === undefined || withinBudget === null) {
    return null;
  }

  const difference = Math.abs(Number(budget) - Number(total));

  return withinBudget ? (
    <p className="budget-status budget-status--ok">
      Cabe no orçamento: sobram {formatMoney(difference, currency)}.
    </p>
  ) : (
    <p className="budget-status budget-status--over">
      Passa do orçamento em {formatMoney(difference, currency)}.
    </p>
  );
}

// ---------------------------------------------------------------------------
// Gastos da viagem
// ---------------------------------------------------------------------------

function TripCosts({ trip }) {
  const currency = trip.currency;
  const travelers = trip.travelers_count;
  const estimate = trip.cost_estimate || {};
  const hasEstimate = Boolean(estimate.total);
  const planned = activitiesTotal(trip);
  const budget = trip.budget === null ? null : Number(trip.budget);

  return (
    <section className="budget-section" aria-labelledby="budget-costs-title">
      <div className="section-heading">
        <div>
          <h2 id="budget-costs-title">Gastos da viagem</h2>
          <p className="muted">
            Valores para {pluralize(travelers, "viajante", "viajantes")}, em{" "}
            {currency}.
          </p>
        </div>
      </div>

      <div className="budget-stats">
        <StatTile
          label="Orçamento"
          value={budget === null ? "Não definido" : formatMoney(budget, currency)}
          detail={
            budget === null
              ? "Defina um orçamento ao editar a viagem."
              : `${formatMoney(perPerson(budget, travelers), currency)} por pessoa`
          }
        />

        <StatTile
          label="Gasto total estimado"
          value={hasEstimate ? formatMoney(estimate.total, currency) : "—"}
          detail={
            hasEstimate
              ? `${formatMoney(estimate.per_person, currency)} por pessoa`
              : "Disponível depois de gerar o roteiro com IA."
          }
          tone={
            estimate.within_budget === true
              ? "ok"
              : estimate.within_budget === false
                ? "over"
                : undefined
          }
        />

        <StatTile
          label="Atividades no roteiro"
          value={formatMoney(planned, currency)}
          detail={`${formatMoney(perPerson(planned, travelers), currency)} por pessoa`}
        />
      </div>

      {hasEstimate ? (
        <div className="budget-card">
          <h3>Como o orçamento se divide</h3>

          <BudgetStatus
            budget={budget}
            total={estimate.total}
            currency={currency}
            withinBudget={estimate.within_budget ?? null}
          />

          <CategoryBreakdown
            categories={estimate}
            total={estimate.total}
            travelers={travelers}
            currency={currency}
          />

          {estimate.notes && (
            <p className="muted budget-note">{estimate.notes}</p>
          )}
        </div>
      ) : (
        <Feedback
          kind="empty"
          title="Ainda não há estimativa por categoria."
          detail="Ela é criada junto com o roteiro gerado pela IA. Enquanto isso, use a calculadora abaixo."
        >
          <ButtonLink to={`/viagens/${trip.id}`} variant="secondary">
            Ir para o roteiro
          </ButtonLink>
        </Feedback>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Calculadora
// ---------------------------------------------------------------------------

function CalculatorResult({ result, onRefresh, busy }) {
  const currency = result.currency;
  const travelers = result.travelers_count;
  const budget = result.budget === null ? null : Number(result.budget);

  let headline;

  if (result.mode === "duration") {
    headline = `${pluralize(result.days, "dia custa", "dias custam")} cerca de ${formatMoney(result.total, currency)}.`;
  } else if (result.days === 0) {
    headline = `Com ${formatMoney(budget, currency)} não dá para fazer nem 1 dia de viagem.`;
  } else {
    headline = `Com ${formatMoney(budget, currency)} dá para ficar até ${pluralize(result.days, "dia", "dias")}${
      result.nights ? ` (${pluralize(result.nights, "noite", "noites")})` : ""
    }.`;
  }

  return (
    <div className="budget-card budget-result" aria-live="polite">
      <h3>{headline}</h3>

      {result.days === 0 ? (
        <p className="budget-status budget-status--over">
          A viagem mínima (1 dia) custa{" "}
          {formatMoney(result.minimum_cost, currency)}. Faltam{" "}
          {formatMoney(Math.abs(Number(result.remaining)), currency)}.
        </p>
      ) : (
        <>
          {result.max_days_reached && (
            <p className="muted">
              O orçamento daria para mais tempo, mas uma viagem pode ter no
              máximo {MAX_DAYS} dias.
            </p>
          )}

          <div className="budget-stats">
            <StatTile
              label="Total"
              value={formatMoney(result.total, currency)}
              detail={pluralize(result.days, "dia", "dias")}
            />
            <StatTile
              label="Por pessoa"
              value={formatMoney(result.per_person, currency)}
              detail={pluralize(travelers, "viajante", "viajantes")}
            />
            <StatTile
              label="Por dia"
              value={formatMoney(result.per_day, currency)}
              detail="para o grupo todo"
            />
          </div>

          <BudgetStatus
            budget={budget}
            total={result.total}
            currency={currency}
            withinBudget={result.within_budget}
          />

          <CategoryBreakdown
            categories={result.categories}
            total={result.total}
            travelers={travelers}
            currency={currency}
          />
        </>
      )}

      <details className="budget-rates">
        <summary>Valores de referência usados</summary>

        <dl>
          {rateLabels.map(([key, label]) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{formatMoney(result.rates[key], currency)}</dd>
            </div>
          ))}
        </dl>

        {result.rates.notes && (
          <p className="muted budget-note">{result.rates.notes}</p>
        )}

        <p className="muted budget-note">
          Estimados pela IA para este destino. Os valores são aproximados.
        </p>

        <Button variant="ghost" onClick={onRefresh} disabled={busy}>
          Pedir novos valores à IA
        </Button>
      </details>
    </div>
  );
}

function CostCalculator({ trip }) {
  const { expireSession } = useAuth();

  const [mode, setMode] = useState("duration");
  const [days, setDays] = useState(String(trip.duration_days || 1));
  const [budget, setBudget] = useState(
    trip.budget === null ? "" : String(Number(trip.budget)),
  );
  const [style, setStyle] = useState(trip.style || "");

  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  const busyRef = useRef(false);

  // Devolve { errors, budgetValue }, com o orçamento já no formato da API.
  function validate() {
    if (mode === "duration") {
      const value = Number(days);
      if (!Number.isInteger(value) || value < 1 || value > MAX_DAYS) {
        return { errors: { days: `Informe de 1 a ${MAX_DAYS} dias.` } };
      }
      return { errors: {} };
    }

    let value;
    try {
      value = normalizeBudget(budget);
    } catch (failure) {
      return { errors: { budget: failure.message } };
    }
    if (!value || Number(value) <= 0) {
      return { errors: { budget: "Informe um orçamento maior que zero." } };
    }
    return { errors: {}, budgetValue: value };
  }

  async function calculate({ refresh = false } = {}) {
    if (busyRef.current) return;

    const { errors, budgetValue } = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    busyRef.current = true;
    setBusy(true);
    setError("");

    try {
      const data = await calculateCosts(trip.id, {
        mode,
        days,
        budget: budgetValue,
        style,
        refresh,
      });
      setResult(data);
    } catch (failure) {
      if (failure.status === 401) {
        expireSession();
        return;
      }

      const fields = failure.fields || {};
      if (fields.days || fields.budget || fields.style) {
        setFieldErrors({
          days: fields.days,
          budget: fields.budget,
          style: fields.style,
        });
      }
      setError(fields.destination || failure.message);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    calculate();
  }

  function changeMode(next) {
    setMode(next);
    setFieldErrors({});
  }

  if (!trip.destination) {
    return (
      <section className="budget-section" aria-labelledby="budget-calc-title">
        <h2 id="budget-calc-title">Calculadora</h2>
        <Feedback
          kind="empty"
          title="Escolha um destino para usar a calculadora."
          detail="Os custos dependem de para onde o grupo vai."
        />
      </section>
    );
  }

  return (
    <section className="budget-section" aria-labelledby="budget-calc-title">
      <div className="section-heading">
        <div>
          <h2 id="budget-calc-title">Calculadora</h2>
          <p className="muted">
            Descubra quanto custa ficar mais ou menos tempo em{" "}
            {trip.destination}, ou quantos dias cabem no seu orçamento.
          </p>
        </div>
      </div>

      <form className="budget-card budget-form" onSubmit={submit} noValidate>
        <fieldset className="budget-modes">
          <legend>O que você quer saber?</legend>

          <label className={`budget-mode ${mode === "duration" ? "is-active" : ""}`}>
            <input
              type="radio"
              name="calculator-mode"
              value="duration"
              checked={mode === "duration"}
              onChange={() => changeMode("duration")}
            />
            <span>
              <strong>Quanto custa?</strong>
              <span className="muted">Custo estimado para uma duração</span>
            </span>
          </label>

          <label className={`budget-mode ${mode === "budget" ? "is-active" : ""}`}>
            <input
              type="radio"
              name="calculator-mode"
              value="budget"
              checked={mode === "budget"}
              onChange={() => changeMode("budget")}
            />
            <span>
              <strong>Quantos dias cabem?</strong>
              <span className="muted">Duração possível para um orçamento</span>
            </span>
          </label>
        </fieldset>

        <div className="budget-form-fields">
          {mode === "duration" ? (
            <Field
              id="calculator-days"
              label="Quantidade de dias"
              hint={`A viagem tem ${pluralize(trip.duration_days, "dia", "dias")} hoje.`}
              error={fieldErrors.days}
            >
              <input
                id="calculator-days"
                type="number"
                inputMode="numeric"
                min="1"
                max={MAX_DAYS}
                value={days}
                onChange={(event) => setDays(event.target.value)}
                aria-invalid={Boolean(fieldErrors.days)}
                aria-describedby={`calculator-days-hint${
                  fieldErrors.days ? " calculator-days-error" : ""
                }`}
              />
            </Field>
          ) : (
            <Field
              id="calculator-budget"
              label={`Orçamento total do grupo (${trip.currency})`}
              hint="Some o que todo o grupo pretende gastar."
              error={fieldErrors.budget}
            >
              <input
                id="calculator-budget"
                type="text"
                inputMode="decimal"
                placeholder="Ex.: 20000"
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
                aria-invalid={Boolean(fieldErrors.budget)}
                aria-describedby={`calculator-budget-hint${
                  fieldErrors.budget ? " calculator-budget-error" : ""
                }`}
              />
            </Field>
          )}

          <Field
            id="calculator-style"
            label="Estilo"
            hint="Mude para simular outro estilo, sem alterar a viagem."
            error={fieldErrors.style}
          >
            <select
              id="calculator-style"
              value={style}
              onChange={(event) => setStyle(event.target.value)}
              aria-describedby="calculator-style-hint"
            >
              <option value="">Não informado</option>
              {travelStyles.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div>
          <Button type="submit" disabled={busy} aria-busy={busy}>
            {busy ? "Calculando…" : "Calcular"}
          </Button>
        </div>
      </form>

      {busy && (
        <Feedback
          kind="loading"
          title="Calculando os custos…"
          detail="Na primeira vez a IA estima os valores do destino, o que pode levar alguns segundos."
        />
      )}

      {error && !busy && (
        <Feedback
          kind="error"
          title="Não foi possível calcular."
          detail={error}
        />
      )}

      {result && !busy && (
        <CalculatorResult
          result={result}
          busy={busy}
          onRefresh={() => calculate({ refresh: true })}
        />
      )}
    </section>
  );
}

export default function BudgetTab({ trip }) {
  return (
    <div className="budget-tab">
      <TripCosts trip={trip} />
      <CostCalculator trip={trip} />
    </div>
  );
}
