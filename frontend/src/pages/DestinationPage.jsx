import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  Link,
  Navigate,
  NavLink,
  useParams,
} from "react-router-dom";

import {
  Badge,
  ButtonLink,
} from "../components/ui";

import Feedback from "../components/Feedback";

import QuestionnaireForm from
  "../components/destinations/QuestionnaireForm";

import DestinationPanel from
  "../components/destinations/DestinationPanel";

import { useAuth } from "../contexts/AuthContext";
import { getTrip } from "../services/trips";

import {
  getMyQuestionnaire,
} from "../services/groupDestinations";

import {
  formatDateRange,
} from "../utils/itinerary";

import "./trip.css";
import "./destination.css";

export default function DestinationPage() {
  const {
    user,
    isRestoring,
    expireSession,
  } = useAuth();

  const { tripId } = useParams();

  if (isRestoring) {
    return (
      <Feedback
        kind="loading"
        title="Verificando sua sessão…"
      />
    );
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  return (
    <DestinationContent
      key={`${user.id}-${tripId}`}
      user={user}
      tripId={tripId}
      expireSession={expireSession}
    />
  );
}

function DestinationContent({
  user,
  tripId,
  expireSession,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [retry, setRetry] = useState(0);
  const [revision, setRevision] = useState(0);
  const [dirty, setDirty] = useState(false);

  const [
    generating,
    setGenerating,
  ] = useState(false);

  const onFailure = useCallback(
    (failure) => {
      if (failure.status === 401) {
        expireSession();
      } else if (
        [403, 404].includes(failure.status)
      ) {
        setError(failure);
      }
    },
    [expireSession],
  );

  useEffect(() => {
    const controller = new AbortController();

    setData(null);
    setError(null);

    Promise.all([
      getTrip(
        tripId,
        { signal: controller.signal },
      ),
      getMyQuestionnaire(
        tripId,
        { signal: controller.signal },
      ),
    ])
      .then(([trip, questionnaire]) => {
        if (!controller.signal.aborted) {
          setData({
            trip,
            questionnaire,
          });
        }
      })
      .catch((failure) => {
        if (controller.signal.aborted) {
          return;
        }

        if (failure.status === 401) {
          expireSession();
        } else {
          setError(failure);
        }
      });

    return () => controller.abort();
  }, [
    tripId,
    retry,
    expireSession,
  ]);

  if (error) {
    const forbidden = [403, 404].includes(
      error.status,
    );

    return (
      <Feedback
        kind="error"
        title={
          forbidden
            ? "Destino do grupo não disponível para sua conta."
            : "Não foi possível carregar o questionário."
        }
        detail={
          forbidden
            ? "Você precisa organizar a viagem ou ter aceitado um convite para participar."
            : error.message
        }
        onRetry={
          forbidden
            ? undefined
            : () =>
                setRetry((value) => value + 1)
        }
      >
        <ButtonLink to="/viagens">
          Ver minhas viagens e convites
        </ButtonLink>
      </Feedback>
    );
  }

  if (!data) {
    return (
      <Feedback
        kind="loading"
        title="Carregando seu questionário…"
      />
    );
  }

  const {
    trip,
    questionnaire,
  } = data;

  return (
    <>
      <nav
        className="breadcrumb"
        aria-label="Você está em"
      >
        <Link to="/viagens">
          Minhas viagens
        </Link>

        <span aria-hidden="true"> / </span>

        <span>
          {trip.title} / Destino ideal
        </span>
      </nav>

      <header className="trip-header">
        <h1>O destino ideal do grupo.</h1>

        <p>{trip.title}</p>

        <div className="trip-header-badges">
          <Badge>
            {formatDateRange(
              trip.start_date,
              trip.end_date,
            )}
          </Badge>

          <Badge>
            {trip.duration_days} dia(s)
          </Badge>
        </div>
      </header>

      <nav
        className="tabs trip-tabs"
        aria-label="Seções da viagem"
      >
        <NavLink
          className="tab"
          to={`/viagens/${trip.id}`}
          end
        >
          Roteiro
        </NavLink>

        <NavLink
          className="tab"
          to={`/viagens/${trip.id}/lugares`}
        >
          Lugares
        </NavLink>

        <NavLink
          className="tab"
          to={`/viagens/${trip.id}/orcamento`}
        >
          Orçamento
        </NavLink>

        <NavLink
          className="tab"
          to={`/viagens/${trip.id}/grupo`}
        >
          Grupo
        </NavLink>

        <NavLink
          className="tab is-active"
          to={`/viagens/${trip.id}/destino`}
          aria-current="page"
        >
          Destino ideal
        </NavLink>
      </nav>

      <div className="destination-page">
        <QuestionnaireForm
          trip={trip}
          answers={questionnaire.answers}
          disabled={generating}
          onDirty={setDirty}
          onSaved={() =>
            setRevision((value) => value + 1)
          }
          onFailure={onFailure}
        />

        <DestinationPanel
          key={revision}
          tripId={trip.id}
          isOwner={trip.owner_id === user.id}
          userId={user.id}
          dirty={dirty}
          onBusy={setGenerating}
          onFailure={onFailure}
        />
      </div>
    </>
  );
}