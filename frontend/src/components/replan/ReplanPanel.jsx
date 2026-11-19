// Painel "Ajustar roteiro" (issue S2-10).
// A pessoa descreve o que quer mudar, escolhe lugares e dias, compara a
// proposta da IA com o roteiro atual e aplica ou descarta.
// Contrato: docs/contratos-api.md, seção "Replanejamento do roteiro".

import { useEffect, useRef, useState } from "react";

import { Button } from "../ui";
import Feedback from "../Feedback";
import { useAuth } from "../../contexts/AuthContext";
import {
  applyProposal,
  createProposal,
  discardProposal,
  getPendingProposal,
} from "../../services/trips";
import {
  categoryLabel,
  formatDayLong,
  formatMoney,
  formatTime,
} from "../../utils/itinerary";
import { pluralize } from "../../utils/places";

import "./replan.css";

const MAX_REQUEST = 500;
const MAX_PLACES = 10;

const decisionLabels = {
  destination: "Destino",
  restaurant: "Restaurante",
  activity: "Atividade",
};

function normalize(title) {
  return (title || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

function ActivityList({ activities, highlight, kind }) {
  if (activities.length === 0) {
    return <p className="muted replan-empty-day">Sem atividades.</p>;
  }

  return (
    <ol className="replan-activities">
      {activities.map((activity, index) => {
        const marked = highlight.has(normalize(activity.title));

        return (
          <li
            key={activity.id ?? `${kind}-${index}`}
            className={marked ? `replan-activity is-${kind}` : "replan-activity"}
          >
            <span className="replan-activity-time">
              {formatTime(activity.start_time) || "—"}
            </span>
            <span className="replan-activity-title">
              {marked && (
                <span className="replan-mark" aria-hidden="true">
                  {kind === "added" ? "+" : "−"}
                </span>
              )}
              {activity.title}
              {marked && (
                <span className="visually-hidden">
                  {kind === "added" ? " (entra)" : " (sai)"}
                </span>
              )}
              <span className="muted replan-activity-category">
                {categoryLabel(activity.category)}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function DayComparison({ day }) {
  const added = new Set(day.added.map(normalize));
  const removed = new Set(day.removed.map(normalize));
  const titleChanged = day.current_title !== day.proposed_title;

  return (
    <li className={`replan-day ${day.changed ? "" : "is-unchanged"}`}>
      <div className="replan-day-heading">
        <h4>
          Dia {day.day_number}
          {day.date && (
            <span className="muted"> · {formatDayLong(day.date)}</span>
          )}
        </h4>

        <p className="muted">
          {day.changed
            ? [
                day.added.length &&
                  pluralize(day.added.length, "entra", "entram"),
                day.removed.length &&
                  pluralize(day.removed.length, "sai", "saem"),
                titleChanged && `novo título: “${day.proposed_title}”`,
              ]
                .filter(Boolean)
                .join(" · ")
            : "Sem mudanças"}
        </p>
      </div>

      {day.changed && (
        <div className="replan-columns">
          <div>
            <p className="replan-column-label">Atual</p>
            <ActivityList
              activities={day.current}
              highlight={removed}
              kind="removed"
            />
          </div>

          <div>
            <p className="replan-column-label">Proposta</p>
            <ActivityList
              activities={day.proposed}
              highlight={added}
              kind="added"
            />
          </div>
        </div>
      )}
    </li>
  );
}

function EstimateComparison({ current, proposed, currency }) {
  if (!proposed?.total) return null;

  const before = Number(current?.total || 0);
  const after = Number(proposed.total);
  const difference = after - before;

  return (
    <p className="replan-estimate">
      Estimativa da viagem:{" "}
      {before > 0 && (
        <>
          {formatMoney(before, currency)} <span aria-hidden="true">→</span>
          <span className="visually-hidden"> passa para </span>{" "}
        </>
      )}
      <strong>{formatMoney(after, currency)}</strong>
      {before > 0 && difference !== 0 && (
        <span className={difference > 0 ? "replan-up" : "replan-down"}>
          {" "}
          ({difference > 0 ? "+" : "−"}
          {formatMoney(Math.abs(difference), currency)})
        </span>
      )}
      {proposed.within_budget === false && (
        <span className="replan-up"> · passa do orçamento</span>
      )}
    </p>
  );
}

export function ProposalView({ proposal, trip, busy, onApply, onDiscard, onNew }) {
  const changedDays = proposal.days.filter((day) => day.changed).length;

  return (
    <div className="replan-proposal">
      <div className="replan-proposal-heading">
        <h3>Proposta de ajuste</h3>
        <p className="muted">
          {proposal.request ? `Pedido: “${proposal.request}”` : "Inclusão de lugares"}
          {proposal.created_by && ` · por ${proposal.created_by.name}`}
        </p>
      </div>

      {proposal.is_outdated && (
        <Feedback
          kind="error"
          title="O roteiro mudou depois desta proposta."
          detail="Para não perder as mudanças feitas, ela não pode mais ser aplicada. Faça um novo pedido."
        />
      )}

      {proposal.summary && <p>{proposal.summary}</p>}

      {proposal.changes.length > 0 && (
        <ul className="replan-changes">
          {proposal.changes.map((change) => (
            <li key={change}>{change}</li>
          ))}
        </ul>
      )}

      {proposal.decisions.length > 0 && (
        <div className="replan-decisions">
          <p className="replan-column-label">Decisões do grupo respeitadas</p>
          <ul>
            {proposal.decisions.map((decision) => (
              <li key={`${decision.category}-${decision.title}`}>
                {decisionLabels[decision.category] || decision.category} ·{" "}
                {decision.title}: <strong>{decision.choice}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      <EstimateComparison
        current={proposal.current_estimate}
        proposed={proposal.estimates}
        currency={trip.currency}
      />

      <p className="muted">
        {changedDays === 0
          ? "A proposta não muda nenhum dia."
          : `${pluralize(changedDays, "dia muda", "dias mudam")}. Nada foi alterado no roteiro ainda.`}
      </p>

      <ul className="replan-days">
        {proposal.days.map((day) => (
          <DayComparison key={day.day_id} day={day} />
        ))}
      </ul>

      {!proposal.can_apply && !proposal.is_outdated && (
        <p className="muted">
          Só a organizadora da viagem pode aplicar. Ela verá esta proposta ao
          abrir o ajuste do roteiro.
        </p>
      )}

      <div className="replan-actions">
        {proposal.can_apply && (
          <Button onClick={onApply} disabled={busy} aria-busy={busy}>
            {busy ? "Aplicando…" : "Aplicar alterações"}
          </Button>
        )}

        {proposal.can_discard && (
          <Button variant="secondary" onClick={onDiscard} disabled={busy}>
            Descartar
          </Button>
        )}

        <Button variant="ghost" onClick={onNew} disabled={busy}>
          Fazer outro pedido
        </Button>
      </div>
    </div>
  );
}

export function RequestForm({ trip, places, busy, onSubmit, onCancelForm }) {
  const [request, setRequest] = useState("");
  const [placeIds, setPlaceIds] = useState([]);
  const [allDays, setAllDays] = useState(true);
  const [dayIds, setDayIds] = useState([]);
  const [errors, setErrors] = useState({});

  function toggle(list, setList, id) {
    setList(
      list.includes(id) ? list.filter((item) => item !== id) : [...list, id],
    );
  }

  function submit(event) {
    event.preventDefault();

    const next = {};
    if (!request.trim() && placeIds.length === 0) {
      next.request = "Descreva o que quer mudar ou escolha lugares para incluir.";
    }
    if (!allDays && dayIds.length === 0) {
      next.day_ids = "Escolha pelo menos um dia.";
    }
    setErrors(next);
    if (Object.keys(next).length) return;

    onSubmit(
      {
        request: request.trim(),
        placeIds,
        dayIds: allDays ? [] : dayIds,
      },
      setErrors,
    );
  }

  return (
    <form className="replan-form" onSubmit={submit} noValidate>
      <div className="field">
        <label htmlFor="replan-request">O que você quer mudar?</label>
        <textarea
          id="replan-request"
          rows={3}
          maxLength={MAX_REQUEST}
          placeholder="Ex.: trocar o museu do dia 2 por um passeio ao ar livre e incluir um jantar de frutos do mar."
          value={request}
          onChange={(event) => setRequest(event.target.value)}
          aria-invalid={Boolean(errors.request)}
          aria-describedby={`replan-request-count${errors.request ? " replan-request-error" : ""}`}
        />
        <p id="replan-request-count" className="muted replan-hint">
          {request.length}/{MAX_REQUEST} caracteres. As decisões das votações
          do grupo são consideradas automaticamente.
        </p>
        {errors.request && (
          <p id="replan-request-error" className="field-error" role="alert">
            {errors.request}
          </p>
        )}
      </div>

      {places.length > 0 && (
        <fieldset className="replan-fieldset">
          <legend>Incluir lugares salvos</legend>
          <div className="replan-options">
            {places.map((place) => {
              const checked = placeIds.includes(place.id);
              return (
                <label key={place.id} className="replan-option">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={!checked && placeIds.length >= MAX_PLACES}
                    onChange={() => toggle(placeIds, setPlaceIds, place.id)}
                  />
                  <span>
                    {place.name}
                    {place.city && <span className="muted"> · {place.city}</span>}
                  </span>
                </label>
              );
            })}
          </div>
          {errors.place_ids && (
            <p className="field-error" role="alert">
              {errors.place_ids}
            </p>
          )}
        </fieldset>
      )}

      <fieldset className="replan-fieldset">
        <legend>Quais dias podem mudar?</legend>
        <label className="replan-option">
          <input
            type="checkbox"
            checked={allDays}
            onChange={() => setAllDays((value) => !value)}
          />
          <span>Todos os dias</span>
        </label>

        {!allDays && (
          <div className="replan-options">
            {trip.days.map((day) => (
              <label key={day.id} className="replan-option">
                <input
                  type="checkbox"
                  checked={dayIds.includes(day.id)}
                  onChange={() => toggle(dayIds, setDayIds, day.id)}
                />
                <span>
                  Dia {day.day_number}
                  <span className="muted"> · {formatDayLong(day.date)}</span>
                </span>
              </label>
            ))}
          </div>
        )}
        {errors.day_ids && (
          <p className="field-error" role="alert">
            {errors.day_ids}
          </p>
        )}
      </fieldset>

      <div className="replan-actions">
        <Button type="submit" disabled={busy} aria-busy={busy}>
          {busy ? "Gerando proposta…" : "Gerar proposta"}
        </Button>
        {onCancelForm && (
          <Button variant="ghost" onClick={onCancelForm} disabled={busy}>
            Voltar para a proposta
          </Button>
        )}
      </div>
    </form>
  );
}

export default function ReplanPanel({ trip, places, onApplied, onClose }) {
  const { expireSession } = useAuth();

  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retry, setRetry] = useState(0);

  const [view, setView] = useState("form");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const busyRef = useRef(false);
  const headingRef = useRef(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError("");

    getPendingProposal(trip.id, { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setProposal(data);
        setView(data ? "proposal" : "form");
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        if (failure.status === 401) expireSession();
        else setLoadError(failure.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [trip.id, retry, expireSession]);

  async function run(action) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setNotice("");

    try {
      await action();
    } catch (failure) {
      if (failure.status === 401) {
        expireSession();
      } else {
        setError(failure.message);
        if (failure.status === 409) {
          // A proposta mudou de situação: recarrega para mostrar o estado real.
          setRetry((value) => value + 1);
        }
      }
      return failure;
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function generate(data, setFieldErrors) {
    run(async () => {
      try {
        const created = await createProposal(trip.id, data);
        setProposal(created);
        setView("proposal");
      } catch (failure) {
        const fields = failure.fields || {};
        if (fields.request || fields.place_ids || fields.day_ids) {
          setFieldErrors(fields);
        }
        throw failure;
      }
    });
  }

  function apply() {
    run(async () => {
      const result = await applyProposal(trip.id, proposal.id);
      setProposal(null);
      setView("form");
      onApplied(result.trip);
      setNotice("Alterações aplicadas ao roteiro.");
    });
  }

  function discard() {
    run(async () => {
      await discardProposal(trip.id, proposal.id);
      setProposal(null);
      setView("form");
      setNotice("Proposta descartada. O roteiro continua como estava.");
    });
  }

  let body;

  if (loading) {
    body = <Feedback kind="loading" title="Carregando o ajuste do roteiro…" />;
  } else if (loadError) {
    body = (
      <Feedback
        kind="error"
        title="Não foi possível carregar o ajuste do roteiro."
        detail={loadError}
        onRetry={() => setRetry((value) => value + 1)}
      />
    );
  } else if (view === "proposal" && proposal) {
    body = (
      <ProposalView
        proposal={proposal}
        trip={trip}
        busy={busy}
        onApply={apply}
        onDiscard={discard}
        onNew={() => setView("form")}
      />
    );
  } else {
    body = (
      <RequestForm
        trip={trip}
        places={places}
        busy={busy}
        onSubmit={generate}
        onCancelForm={proposal ? () => setView("proposal") : null}
      />
    );
  }

  return (
    <section className="replan-panel" aria-labelledby="replan-title">
      <div className="replan-panel-heading">
        <div>
          <h2 id="replan-title" ref={headingRef} tabIndex={-1}>
            Ajustar roteiro
          </h2>
          <p className="muted">
            A IA propõe as mudanças e você compara antes de aplicar.
          </p>
        </div>

        <Button variant="ghost" onClick={onClose} disabled={busy}>
          Fechar
        </Button>
      </div>

      {notice && <Feedback kind="success" title={notice} />}

      {busy && view === "form" && (
        <Feedback
          kind="loading"
          title="Gerando a proposta…"
          detail="Isso pode levar até um minuto. O roteiro atual não muda até você aplicar."
        />
      )}

      {error && !busy && (
        <Feedback kind="error" title="Não foi possível concluir." detail={error} />
      )}

      {body}
    </section>
  );
}
