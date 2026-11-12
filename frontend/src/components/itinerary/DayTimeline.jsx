import { useState } from "react";

import { Button } from "../ui";

import {
  categoryLabel,
  formatActivityCost,
  formatDuration,
  formatTime,
  hasCoordinates,
} from "../../utils/itinerary";

/*
  Lista das atividades de um dia, em linha do tempo.
  - mapNumbers: Map(activityId -> número do ponto no mapa).
  - As ações devolvem Promises; erros aparecem acima da lista.
*/
export default function DayTimeline({
  day,
  currency,
  mapNumbers,
  activeId,
  onShowOnMap,
  onEdit,
  onDelete,
  onMove,
}) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(null);

  async function run(key, action) {
    setBusy(key);
    setError("");

    try {
      await action();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy("");
    }
  }

  const activities = day.activities;

  return (
    <div className="timeline-wrapper">
      {error && (
        <p className="place-form-error" role="alert">
          {error}
        </p>
      )}

      <ol className="timeline" aria-label={`Atividades do dia ${day.day_number}`}>
        {activities.map((activity, index) => {
          const number = mapNumbers.get(activity.id);
          const meta = [
            formatDuration(activity.duration_minutes),
            categoryLabel(activity.category),
            formatActivityCost(activity, currency),
          ].filter(Boolean);

          return (
            <li
              key={activity.id}
              className={`timeline-item ${
                activeId === activity.id ? "is-active" : ""
              }`}
            >
              <div className="timeline-time">
                {formatTime(activity.start_time) || "—"}
                {activity.end_time && (
                  <span className="muted">
                    {formatTime(activity.end_time)}
                  </span>
                )}
              </div>

              <div className="timeline-dot" aria-hidden="true" />

              <article className="timeline-card">
                {activity.image_url && (
                  <img
                    className="timeline-image"
                    src={activity.image_url}
                    alt=""
                    loading="lazy"
                    onError={(event) => {
                      event.currentTarget.hidden = true;
                    }}
                  />
                )}

                <div className="timeline-body">
                  <h3>{activity.title}</h3>

                  <p className="muted timeline-meta">{meta.join(" · ")}</p>

                  {(activity.location_name || activity.address) && (
                    <p className="timeline-location">
                      {number ? (
                        <button
                          type="button"
                          className="timeline-pin"
                          onClick={() => onShowOnMap(activity.id)}
                          aria-label={`Ver ponto ${number} no mapa: ${
                            activity.location_name || activity.title
                          }`}
                        >
                          {number}
                        </button>
                      ) : null}
                      {[activity.location_name, activity.address]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  )}

                  {!hasCoordinates(activity) && (
                    <p className="timeline-no-map">Sem localização no mapa</p>
                  )}

                  {activity.description && (
                    <p className="timeline-text">{activity.description}</p>
                  )}

                  {activity.notes && (
                    <p className="timeline-notes">
                      <strong>Observações:</strong> {activity.notes}
                    </p>
                  )}

                  {confirming === activity.id ? (
                    <div className="timeline-confirm" role="alert">
                      <span>Remover “{activity.title}” do roteiro?</span>
                      <Button
                        variant="ghost"
                        onClick={() => setConfirming(null)}
                        disabled={Boolean(busy)}
                      >
                        Cancelar
                      </Button>
                      <Button
                        className="button--danger"
                        onClick={() =>
                          run(`delete-${activity.id}`, async () => {
                            await onDelete(activity);
                            setConfirming(null);
                          })
                        }
                        disabled={Boolean(busy)}
                      >
                        {busy === `delete-${activity.id}`
                          ? "Removendo…"
                          : "Remover"}
                      </Button>
                    </div>
                  ) : (
                    <div className="timeline-actions">
                      <button
                        type="button"
                        onClick={() => onEdit(activity)}
                        disabled={Boolean(busy)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirming(activity.id)}
                        disabled={Boolean(busy)}
                      >
                        Remover
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          run(`move-${activity.id}`, () =>
                            onMove(activity, index - 1),
                          )
                        }
                        disabled={Boolean(busy) || index === 0}
                        aria-label={`Subir ${activity.title}`}
                      >
                        ↑ Subir
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          run(`move-${activity.id}`, () =>
                            onMove(activity, index + 1),
                          )
                        }
                        disabled={
                          Boolean(busy) || index === activities.length - 1
                        }
                        aria-label={`Descer ${activity.title}`}
                      >
                        ↓ Descer
                      </button>
                    </div>
                  )}
                </div>
              </article>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
