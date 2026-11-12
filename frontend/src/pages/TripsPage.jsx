import { useEffect, useState } from "react";

import {
  Link,
  Navigate,
  useLocation,
  useSearchParams,
} from "react-router-dom";

import {
  Badge,
  Button,
  ButtonLink,
  Card,
  PageHeading,
} from "../components/ui";

import { useAuth } from "../contexts/AuthContext";
import { listTrips } from "../services/trips";

import {
  formatTripBudget,
  formatTripDate,
  tripStatuses,
} from "../utils/tripForm";

import "./trips.css";

const statusLabels = {
  planning: "Em planejamento",
  upcoming: "Próxima",
  completed: "Realizada",
};

export default function TripsPage({
  history = false,
}) {
  const {
    user,
    isRestoring,
    token,
    expireSession,
  } = useAuth();

  const [params] = useSearchParams();
  const location = useLocation();

  const selected = params.get("status");

  const status = history
    ? "completed"
    : tripStatuses.some(([value]) => value === selected)
      ? selected
      : "planning";

  const [result, setResult] = useState({
    status: "",
    trips: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  const userId = user?.id;

  useEffect(() => {
    if (!userId) {
      return;
    }

    const controller = new AbortController();

    setLoading(true);
    setError("");

    listTrips({
      status,
      token,
      signal: controller.signal,
    })
      .then((trips) => {
        if (controller.signal.aborted) {
          return;
        }

        if (!Array.isArray(trips)) {
          throw new Error(
            "Não foi possível interpretar a lista de viagens.",
          );
        }

        const sorted = [...trips].sort((a, b) =>
          status === "completed"
            ? b.end_date.localeCompare(a.end_date)
            : a.start_date.localeCompare(b.start_date),
        );

        setResult({
          status,
          trips: sorted,
        });
      })
      .catch((failure) => {
        if (controller.signal.aborted) {
          return;
        }

        if (failure.status === 401) {
          expireSession();
        } else {
          setError(failure.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [
    userId,
    status,
    token,
    retry,
    expireSession,
  ]);

  if (isRestoring) {
    return (
      <p role="status">
        Verificando sua sessão…
      </p>
    );
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  const busy = loading || result.status !== status;

  const emptyText =
    status === "completed"
      ? "Suas viagens realizadas aparecerão aqui."
      : status === "upcoming"
        ? "Você ainda não tem viagens marcadas como próximas."
        : "Seu próximo capítulo começa com um novo plano.";

  return (
    <>
      <PageHeading
        eyebrow={
          history
            ? "Suas memórias"
            : "Seu próximo capítulo"
        }
        title={
          history
            ? "Histórico de viagens."
            : `Olá, ${user.first_name || "viajante"}. Para onde vamos?`
        }
        description={
          history
            ? "Relembre os lugares e os caminhos que você já percorreu."
            : "Suas viagens, seus lugares e as pessoas que vão com você."
        }
        action={
          <ButtonLink to="/viagens/nova">
            + Planejar viagem
          </ButtonLink>
        }
      />

      {location.state?.createdTripId && !history && (
        <p role="status" className="trips-success">
          Viagem criada com sucesso.
        </p>
      )}

      {history ? (
        <Link to="/viagens" className="trips-back">
          ← Ver minhas viagens
        </Link>
      ) : (
        <nav
          className="trip-filters"
          aria-label="Situação das viagens"
        >
          {tripStatuses.map(([value, label]) => (
            <Link
              key={value}
              to={`/viagens?status=${value}`}
              className={`button button--${
                status === value
                  ? "primary"
                  : "secondary"
              }`}
              aria-current={
                status === value
                  ? "page"
                  : undefined
              }
            >
              {label}
            </Link>
          ))}
        </nav>
      )}

      {error ? (
        <Card className="trips-empty">
          <p role="alert">{error}</p>

          <Button
            onClick={() =>
              setRetry((value) => value + 1)
            }
          >
            Tentar novamente
          </Button>
        </Card>
      ) : busy ? (
        <p role="status">Carregando viagens…</p>
      ) : result.trips.length === 0 ? (
        <Card className="trips-empty">
          <h2>
            {status === "completed"
              ? "Ainda há muitas histórias pela frente."
              : "Um novo plano espera por você."}
          </h2>

          <p className="muted">{emptyText}</p>

          <ButtonLink to="/viagens/nova">
            Planejar viagem
          </ButtonLink>
        </Card>
      ) : (
        <div className="trips-grid">
          {result.trips.map((trip, index) => (
            <Card
              key={trip.id}
              className={`trip-card ${
                index === 0
                  ? "trip-card-featured"
                  : ""
              }`}
            >
              <div
                className="trip-cover"
                aria-hidden="true"
              >
                {trip.cover_image_url && (
                  <img
                    src={trip.cover_image_url}
                    alt=""
                    loading="lazy"
                    onError={(event) => {
                      event.currentTarget.hidden = true;
                    }}
                  />
                )}

                <span>
                  {trip.destination ||
                    "O destino pode esperar."}
                </span>
              </div>

              <div className="trip-card-body">
                <Badge>
                  {statusLabels[trip.status] ||
                    trip.status}
                </Badge>

                <h2>{trip.title}</h2>

                <p className="muted">
                  {trip.origin} →{" "}
                  {trip.destination ||
                    "Destino a decidir"}
                </p>

                <p>
                  {formatTripDate(trip.start_date)}
                  {" — "}
                  {formatTripDate(trip.end_date)}
                </p>

                <p className="muted">
                  {trip.duration_days}{" "}
                  {trip.duration_days === 1
                    ? "dia"
                    : "dias"}
                  {" · "}
                  {trip.travelers_count}{" "}
                  {trip.travelers_count === 1
                    ? "viajante"
                    : "viajantes"}
                </p>

                <p className="trip-budget">
                  {formatTripBudget(
                    trip.budget,
                    trip.currency,
                  )}
                </p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}