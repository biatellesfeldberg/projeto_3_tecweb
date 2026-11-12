import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  Link,
  Navigate,
  NavLink,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

import { Badge, Button, ButtonLink } from "../components/ui";
import Feedback from "../components/Feedback";
import TripMap from "../components/TripMap";
import DayTimeline from "../components/itinerary/DayTimeline";
import DayNotes from "../components/itinerary/DayNotes";
import ActivityFormDialog from "../components/itinerary/ActivityFormDialog";
import TripPlacesTab from "../components/itinerary/TripPlacesTab";

import { useAuth } from "../contexts/AuthContext";
import {
  createActivity,
  deleteActivity,
  generateItinerary,
  getTrip,
  reorderActivities,
  updateActivity,
  updateDay,
} from "../services/trips";
import {
  addPlacesToTrip,
  listTripPlaces,
  removePlaceFromTrip,
} from "../services/places";

import {
  countActivities,
  formatDateRange,
  formatDayChip,
  formatDayLong,
  formatTime,
  hasCoordinates,
  placeToActivityForm,
  tripStatusLabels,
} from "../utils/itinerary";
import { pluralize } from "../utils/places";

import "./places.css";
import "./trip.css";

export default function TripPage({ tab = "roteiro" }) {
  const { tripId } = useParams();
  const { user, isRestoring, expireSession } = useAuth();
  const userId = user?.id;

  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retry, setRetry] = useState(0);

  const [places, setPlaces] = useState([]);
  const [placesLoading, setPlacesLoading] = useState(true);
  const [placesError, setPlacesError] = useState("");
  const [placesRetry, setPlacesRetry] = useState(0);

  const [dialog, setDialog] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const generatingRef = useRef(false);

  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();

  const handleFailure = useCallback(
    (failure) => {
      if (failure.status === 401) expireSession();
      throw failure;
    },
    [expireSession],
  );

  // Viagem com dias e atividades.
  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    getTrip(tripId, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setTrip(data);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        if (failure.status === 401) {
          expireSession();
        } else {
          setError(failure);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [userId, tripId, retry, expireSession]);

  // Lugares salvos vinculados à viagem.
  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();
    setPlacesLoading(true);
    setPlacesError("");

    listTripPlaces(tripId, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setPlaces(data);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        if (failure.status === 401) {
          expireSession();
        } else {
          setPlacesError(failure.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setPlacesLoading(false);
      });

    return () => controller.abort();
  }, [userId, tripId, placesRetry, expireSession]);

  // Dia selecionado (?dia=N), com o primeiro dia como padrão.
  const days = trip?.days || [];
  const requested = Number(params.get("dia"));
  const day =
    days.find((item) => item.day_number === requested) || days[0] || null;

  // Pontos do mapa: só atividades com coordenadas válidas, na ordem do dia.
  const points = useMemo(() => {
    if (!day) return [];
    return day.activities.filter(hasCoordinates).map((activity, index) => ({
      id: activity.id,
      lat: Number(activity.latitude),
      lng: Number(activity.longitude),
      label: index + 1,
      title: activity.title,
      detail: [formatTime(activity.start_time), activity.location_name]
        .filter(Boolean)
        .join(" · "),
    }));
  }, [day]);

  const mapNumbers = useMemo(
    () => new Map(points.map((point) => [point.id, point.label])),
    [points],
  );

  if (isRestoring) {
    return <Feedback kind="loading" title="Verificando sua sessão…" />;
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  if (error) {
    return error.status === 404 ? (
      <Feedback
        kind="empty"
        title="Viagem não encontrada."
        detail="Ela pode ter sido excluída ou não pertencer à sua conta."
      >
        <ButtonLink to="/viagens">Ver minhas viagens</ButtonLink>
      </Feedback>
    ) : (
      <Feedback
        kind="error"
        title="Não foi possível carregar a viagem."
        detail={error.message}
        onRetry={() => setRetry((value) => value + 1)}
      />
    );
  }

  if (loading && !trip) {
    return <Feedback kind="loading" title="Carregando a viagem…" />;
  }

  // -------------------------------------------------------------------------
  // Atualizações locais a partir das respostas da API
  // -------------------------------------------------------------------------

  function replaceDay(updated) {
    setTrip((current) => ({
      ...current,
      days: current.days.map((item) =>
        item.id === updated.id ? updated : item,
      ),
    }));
  }

  // Criar, editar ou remover atividades pode mudar ordem e dia: recarrega a
  // viagem para ficar igual ao servidor.
  async function refreshTrip() {
    const data = await getTrip(tripId).catch(handleFailure);
    setTrip(data);
  }

  function selectDay(dayNumber) {
    const next = new URLSearchParams(params);
    next.set("dia", dayNumber);
    setParams(next, { replace: true });
    setActiveId(null);
  }

  // -------------------------------------------------------------------------
  // Ações
  // -------------------------------------------------------------------------

  async function saveActivity(payload) {
    if (dialog?.activity) {
      await updateActivity(trip.id, dialog.activity.id, payload).catch(
        handleFailure,
      );
    } else {
      await createActivity(trip.id, payload).catch(handleFailure);
    }

    await refreshTrip();
    setDialog(null);

    // Mostra o dia onde a atividade ficou.
    const target = trip.days.find((item) => item.id === payload.day);
    if (target && tab !== "roteiro") {
      navigate(`/viagens/${trip.id}?dia=${target.day_number}`);
    } else if (target && target.id !== day?.id) {
      selectDay(target.day_number);
    }
  }

  async function removeActivity(activity) {
    await deleteActivity(trip.id, activity.id).catch(handleFailure);
    await refreshTrip();
  }

  async function moveActivity(activity, newIndex) {
    const ids = day.activities.map((item) => item.id);
    const from = ids.indexOf(activity.id);
    if (newIndex < 0 || newIndex >= ids.length || from === newIndex) return;

    ids.splice(from, 1);
    ids.splice(newIndex, 0, activity.id);

    const updated = await reorderActivities(trip.id, day.id, ids).catch(
      handleFailure,
    );
    replaceDay(updated);
  }

  async function saveDay(data) {
    const updated = await updateDay(trip.id, day.id, data).catch(
      handleFailure,
    );
    replaceDay(updated);
  }

  async function generate() {
    if (generatingRef.current) return;
    generatingRef.current = true;
    setGenerating(true);
    setGenerationError("");

    try {
      const updated = await generateItinerary(trip.id, {
        replaceExisting: false,
      });
      setTrip(updated);
    } catch (failure) {
      if (failure.status === 401) {
        expireSession();
      } else {
        setGenerationError(failure.message);
      }
    } finally {
      generatingRef.current = false;
      setGenerating(false);
    }
  }

  async function addPlaces(ids) {
    const data = await addPlacesToTrip(trip.id, ids).catch(handleFailure);
    setPlaces(data);
  }

  async function removePlace(place) {
    await removePlaceFromTrip(trip.id, place.id).catch(handleFailure);
    setPlaces((current) => current.filter((item) => item.id !== place.id));
  }

  // -------------------------------------------------------------------------
  // Tela
  // -------------------------------------------------------------------------

  const total = countActivities(trip);
  const emptyDays = days.filter((item) => item.activities.length === 0).length;
  const withoutLocation = day
    ? day.activities.length - points.length
    : 0;

  const generationBlock = trip.destination ? (
    <div className="generation-block">
      <Button
        variant={total === 0 ? "primary" : "secondary"}
        onClick={generate}
        disabled={generating}
        aria-busy={generating}
      >
        {generating
          ? "Montando seu roteiro…"
          : total === 0
            ? "Gerar roteiro com IA"
            : `Preencher ${pluralize(emptyDays, "dia vazio", "dias vazios")} com IA`}
      </Button>

      {generating && (
        <Feedback
          kind="loading"
          title="Montando seu roteiro…"
          detail="Isso pode levar até um minuto. As atividades que você já tem são mantidas."
        />
      )}

      {generationError && (
        <Feedback
          kind="error"
          title="Não foi possível gerar o roteiro."
          detail={generationError}
        />
      )}
    </div>
  ) : null;

  let content;

  if (tab === "lugares") {
    content = (
      <TripPlacesTab
        trip={trip}
        places={places}
        loading={placesLoading}
        error={placesError}
        onRetry={() => setPlacesRetry((value) => value + 1)}
        onAdd={addPlaces}
        onRemove={removePlace}
        onAddToItinerary={(place) =>
          setDialog({
            type: "activity",
            initial: placeToActivityForm(place, day?.id),
          })
        }
      />
    );
  } else if (days.length === 0) {
    content = (
      <Feedback
        kind="empty"
        title="Esta viagem ainda não tem dias."
        detail="Confira as datas da viagem."
      />
    );
  } else {
    content = (
      <>
        <div className="day-heading">
          <div>
            <h2>{formatDayLong(day.date)}</h2>
            <p className="muted">
              Dia {day.day_number} de {days.length}
              {day.title ? ` · ${day.title}` : ""}
            </p>
          </div>

          <Button
            variant="secondary"
            onClick={() =>
              setDialog({ type: "activity", initial: { day: String(day.id) } })
            }
          >
            + Adicionar atividade
          </Button>
        </div>

        <nav className="day-chips" aria-label="Dias da viagem">
          {days.map((item) => {
            const chip = formatDayChip(item.date);
            const current = item.id === day.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`chip day-chip ${current ? "is-active" : ""}`}
                aria-current={current ? "date" : undefined}
                aria-label={`${formatDayLong(item.date)}, ${pluralize(
                  item.activities.length,
                  "atividade",
                  "atividades",
                )}`}
                onClick={() => selectDay(item.day_number)}
              >
                {chip.day} {chip.weekday}
                {item.activities.length === 0 && (
                  <span className="day-chip-empty" aria-hidden="true" />
                )}
              </button>
            );
          })}
        </nav>

        {total === 0 ? (
          <Feedback
            kind="empty"
            title="O roteiro ainda está em branco."
            detail={
              trip.destination
                ? "Peça à IA uma primeira versão ou adicione as atividades você mesmo."
                : "Escolha um destino para gerar o roteiro com IA, ou adicione as atividades você mesmo."
            }
          >
            {generationBlock}
          </Feedback>
        ) : (
          emptyDays > 0 && generationBlock
        )}

        <div className="itinerary-layout">
          <section aria-label="Lista de atividades">
            {day.activities.length === 0 ? (
              <div className="timeline-empty">
                <p>Nenhuma atividade neste dia.</p>
                <Button
                  variant="ghost"
                  onClick={() =>
                    setDialog({
                      type: "activity",
                      initial: { day: String(day.id) },
                    })
                  }
                >
                  + Adicionar atividade
                </Button>
              </div>
            ) : (
              <DayTimeline
                key={day.id}
                day={day}
                currency={trip.currency}
                mapNumbers={mapNumbers}
                activeId={activeId}
                onShowOnMap={setActiveId}
                onEdit={(activity) =>
                  setDialog({ type: "activity", activity })
                }
                onDelete={removeActivity}
                onMove={moveActivity}
              />
            )}

            <DayNotes key={`notes-${day.id}`} day={day} onSave={saveDay} />
          </section>

          <aside className="itinerary-map">
            <p className="itinerary-map-label">
              {points.length > 0
                ? `Trajeto do dia · ${pluralize(points.length, "lugar", "lugares")}`
                : "Nenhuma atividade deste dia tem localização"}
            </p>
            <TripMap
              points={points}
              route
              activeId={activeId}
              onSelect={setActiveId}
              label={`Mapa do dia ${day.day_number}`}
            />
            {withoutLocation > 0 && points.length > 0 && (
              <p className="muted itinerary-map-note">
                {pluralize(
                  withoutLocation,
                  "atividade sem coordenadas não aparece",
                  "atividades sem coordenadas não aparecem",
                )}{" "}
                no mapa, só na lista.
              </p>
            )}
          </aside>
        </div>
      </>
    );
  }

  return (
    <>
      <nav className="breadcrumb" aria-label="Você está em">
        <Link to="/viagens">Minhas viagens</Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">{trip.title}</span>
      </nav>

      <header className="trip-header">
        <h1>{trip.title}</h1>
        <div className="trip-header-badges">
          <Badge>{formatDateRange(trip.start_date, trip.end_date)}</Badge>
          <Badge>
            {pluralize(trip.travelers_count, "viajante", "viajantes")}
          </Badge>
          <Badge>{tripStatusLabels[trip.status] || trip.status}</Badge>
          {trip.destination && <Badge>{trip.destination}</Badge>}
        </div>
        {trip.ai_summary && tab === "roteiro" && (
          <p className="trip-summary">{trip.ai_summary}</p>
        )}
      </header>

      <nav className="tabs trip-tabs" aria-label="Seções da viagem">
        <NavLink
          to={`/viagens/${trip.id}`}
          end
          className={({ isActive }) => `tab ${isActive ? "is-active" : ""}`}
        >
          Roteiro
        </NavLink>
        <NavLink
          to={`/viagens/${trip.id}/lugares`}
          className={({ isActive }) => `tab ${isActive ? "is-active" : ""}`}
        >
          Lugares{places.length > 0 ? ` (${places.length})` : ""}
        </NavLink>
      </nav>

      {content}

      <ActivityFormDialog
        open={dialog?.type === "activity"}
        activity={dialog?.activity || null}
        initial={dialog?.initial}
        days={days}
        places={places}
        currency={trip.currency}
        onClose={() => setDialog(null)}
        onSave={saveActivity}
      />
    </>
  );
}

