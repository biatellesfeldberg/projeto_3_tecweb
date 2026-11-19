import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Link,
  Navigate,
  NavLink,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  Badge,
  Button,
  ButtonLink,
} from "../components/ui";

import Feedback from "../components/Feedback";
import GroupMembers from "../components/group/GroupMembers";
import GroupPolls from "../components/group/GroupPolls";

import { useAuth } from "../contexts/AuthContext";
import { getTrip } from "../services/trips";

import {
  closePoll,
  createPoll,
  getPoll,
  groupError,
  inviteMember,
  leaveGroup,
  listMembers,
  listPolls,
  removeMember,
  voteInPoll,
} from "../services/groups";

import {
  formatDateRange,
} from "../utils/itinerary";

import "./trip.css";
import "../components/group/group.css";

export default function GroupPage() {
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
    <GroupContent
      key={`${user.id}-${tripId}`}
      user={user}
      tripId={tripId}
      expireSession={expireSession}
    />
  );
}

function GroupContent({
  user,
  tripId,
  expireSession,
}) {
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const actionRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setError(null);

    Promise.all([
      getTrip(
        tripId,
        { signal: controller.signal },
      ),
      listMembers(
        tripId,
        { signal: controller.signal },
      ),
      listPolls(
        tripId,
        { signal: controller.signal },
      ),
    ])
      .then(([trip, members, polls]) => {
        if (controller.signal.aborted) {
          return;
        }

        if (
          !trip.id ||
          !members.owner ||
          !Array.isArray(members.members) ||
          !Array.isArray(polls)
        ) {
          throw new Error(
            "O servidor retornou os dados do grupo em formato inesperado.",
          );
        }

        setData({
          trip,
          members,
          polls,
        });
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
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [
    tripId,
    retry,
    expireSession,
  ]);

  useEffect(
    () => () => actionRef.current?.abort(),
    [],
  );

  async function perform(
    message,
    operation,
    update,
  ) {
    if (actionRef.current) {
      return {
        ok: false,
        error: "Aguarde a ação atual terminar.",
      };
    }

    const controller = new AbortController();

    actionRef.current = controller;

    setBusy(true);
    setNotice("");

    try {
      const result = await operation({
        signal: controller.signal,
      });

      if (controller.signal.aborted) {
        return {
          ok: false,
          error: "",
        };
      }

      update?.(result);
      setNotice(message);

      return {
        ok: true,
        data: result,
      };
    } catch (failure) {
      if (controller.signal.aborted) {
        return {
          ok: false,
          error: "",
        };
      }

      if (failure.status === 401) {
        expireSession();
      } else if (
        failure.status === 403 ||
        failure.status === 404
      ) {
        setRetry((value) => value + 1);
      }

      return {
        ok: false,
        error: groupError(failure),
      };
    } finally {
      if (!controller.signal.aborted) {
        actionRef.current = null;
        setBusy(false);
      }
    }
  }

  function replacePoll(updated) {
    setData((current) => ({
      ...current,
      polls: current.polls.map(
        (poll) =>
          poll.id === updated.id
            ? updated
            : poll,
      ),
    }));
  }

  if (loading) {
    return (
      <Feedback
        kind="loading"
        title="Carregando o grupo…"
      />
    );
  }

  if (error) {
    return (
      <Feedback
        kind={
          error.status === 404
            ? "empty"
            : "error"
        }
        title={
          error.status === 404
            ? "Grupo não disponível para sua conta."
            : "Não foi possível carregar o grupo."
        }
        detail={
          error.status === 404
            ? "Você precisa ser a organizadora ou ter aceitado um convite. Confira os convites em Minhas viagens."
            : groupError(error)
        }
        onRetry={
          error.status === 404
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

  const {
    trip,
    members,
    polls,
  } = data;

  const owner =
    members.owner.id === user.id;

  return (
    <>
      <nav
        className="breadcrumb"
        aria-label="Você está em"
      >
        <Link to="/viagens">
          Minhas viagens
        </Link>

        <span> / </span>

        <span>
          {trip.title} / Grupo
        </span>
      </nav>

      <header className="trip-header">
        <h1>{trip.title}</h1>

        <div className="trip-header-badges">
          <Badge>
            {formatDateRange(
              trip.start_date,
              trip.end_date,
            )}
          </Badge>

          <Badge>
            {owner
              ? "Você organiza esta viagem"
              : "Você participa desta viagem"}
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
          className="tab is-active"
          to={`/viagens/${trip.id}/grupo`}
          aria-current="page"
        >
          Grupo
        </NavLink>
      </nav>

      <div className="group-page">
        <ButtonLink
          to={`/viagens/${trip.id}/destino`}
        >
          Responder questionário e ver destino ideal
        </ButtonLink>

        {notice && (
          <Feedback
            kind="success"
            title={notice}
          />
        )}

        <Button
          variant="ghost"
          disabled={busy}
          onClick={() =>
            setRetry((value) => value + 1)
          }
        >
          Atualizar grupo e votações
        </Button>

        <GroupMembers
          owner={members.owner}
          members={members.members}
          isOwner={owner}
          busy={busy}
          expireSession={expireSession}
          onInvite={(id) =>
            perform(
              "Convite enviado.",
              (options) =>
                inviteMember(
                  trip.id,
                  id,
                  options,
                ),
              (member) =>
                setData((current) => ({
                  ...current,
                  members: {
                    ...current.members,
                    members: [
                      ...current.members.members,
                      member,
                    ],
                  },
                })),
            )
          }
          onRemove={(member) =>
            perform(
              member.status === "pending"
                ? "Convite cancelado."
                : "Integrante removido.",
              (options) =>
                removeMember(
                  trip.id,
                  member.user.id,
                  options,
                ),
              () =>
                setRetry((value) => value + 1),
            )
          }
          onLeave={() =>
            perform(
              "Você saiu do grupo.",
              (options) =>
                leaveGroup(
                  trip.id,
                  options,
                ),
              () =>
                navigate(
                  "/viagens",
                  { replace: true },
                ),
            )
          }
        />

        <GroupPolls
          polls={polls}
          isOwner={owner}
          busy={busy}
          owner={members.owner}
          onCreate={(payload) =>
            perform(
              "Votação criada.",
              (options) =>
                createPoll(
                  trip.id,
                  payload,
                  options,
                ),
              (poll) =>
                setData((current) => ({
                  ...current,
                  polls: [
                    poll,
                    ...current.polls,
                  ],
                })),
            )
          }
          onVote={(id, optionId) =>
            perform(
              "Voto salvo.",
              (options) =>
                voteInPoll(
                  trip.id,
                  id,
                  optionId,
                  options,
                ),
              replacePoll,
            )
          }
          onClose={(id, payload) =>
            perform(
              "Votação encerrada e decisão registrada.",
              (options) =>
                closePoll(
                  trip.id,
                  id,
                  payload,
                  options,
                ),
              replacePoll,
            )
          }
          onRefresh={(id) =>
            perform(
              "Resultados atualizados.",
              (options) =>
                getPoll(
                  trip.id,
                  id,
                  options,
                ),
              replacePoll,
            )
          }
        />
      </div>
    </>
  );
}