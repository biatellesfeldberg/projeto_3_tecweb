import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../ui";
import Feedback from "../Feedback";

import { useAuth } from "../../contexts/AuthContext";

import {
  acceptInvitation,
  groupError,
  listInvitations,
  rejectInvitation,
} from "../../services/groups";

import "./group.css";

export default function TripInvitations() {
  const { expireSession } = useAuth();
  const navigate = useNavigate();

  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);

  const actionRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setLoadError("");

    listInvitations({
      signal: controller.signal,
    })
      .then((items) => {
        if (controller.signal.aborted) return;

        if (!Array.isArray(items)) {
          throw new Error(
            "Lista de convites em formato inesperado.",
          );
        }

        setInvitations(items);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;

        if (failure.status === 401) {
          expireSession();
        } else {
          setLoadError(groupError(failure));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [retry, expireSession]);

  useEffect(
    () => () => actionRef.current?.abort(),
    [],
  );

  async function answer(invitation, accept) {
    if (actionRef.current) return;

    const controller = new AbortController();
    actionRef.current = controller;

    setBusy(true);
    setError("");
    setNotice("");

    try {
      const action = accept
        ? acceptInvitation
        : rejectInvitation;

      await action(invitation.id, {
        signal: controller.signal,
      });

      if (controller.signal.aborted) return;

      setInvitations((items) =>
        items.filter(
          (item) => item.id !== invitation.id,
        ),
      );

      if (accept) {
        navigate(
          `/viagens/${invitation.trip}/grupo`,
        );
      } else {
        setNotice("Convite recusado.");
      }
    } catch (failure) {
      if (controller.signal.aborted) return;

      if (failure.status === 401) {
        expireSession();
      } else {
        setError(groupError(failure));

        if (failure.status === 404) {
          setRetry((value) => value + 1);
        }
      }
    } finally {
      if (!controller.signal.aborted) {
        actionRef.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <section
      className="card group-invitations"
      aria-labelledby="trip-invitations-title"
    >
      <div className="section-heading">
        <h2 id="trip-invitations-title">
          Convites de viagem
        </h2>

        <Button
          variant="ghost"
          disabled={busy || loading}
          onClick={() =>
            setRetry((value) => value + 1)
          }
        >
          Atualizar convites
        </Button>
      </div>

      {notice && (
        <Feedback
          kind="success"
          title={notice}
        />
      )}

      {error && (
        <Feedback
          kind="error"
          title="Não foi possível responder ao convite."
          detail={error}
        />
      )}

      {loading ? (
        <Feedback
          kind="loading"
          title="Carregando convites…"
        />
      ) : loadError ? (
        <Feedback
          kind="error"
          title="Não foi possível carregar os convites."
          detail={loadError}
          onRetry={() =>
            setRetry((value) => value + 1)
          }
        />
      ) : invitations.length ? (
        <ul
          className="group-people"
          aria-label="Convites de viagem recebidos"
        >
          {invitations.map((invitation) => (
            <li
              className="group-person"
              key={invitation.id}
            >
              <div>
                <h3>{invitation.trip_title}</h3>

                <p className="muted">
                  Convite de{" "}
                  {[
                    invitation.invited_by.first_name,
                    invitation.invited_by.last_name,
                  ]
                    .filter(Boolean)
                    .join(" ")}
                </p>
              </div>

              <div className="group-actions">
                <Button
                  disabled={busy}
                  aria-label={`Aceitar convite para ${invitation.trip_title}`}
                  onClick={() =>
                    answer(invitation, true)
                  }
                >
                  Aceitar convite
                </Button>

                <Button
                  variant="secondary"
                  disabled={busy}
                  aria-label={`Recusar convite para ${invitation.trip_title}`}
                  onClick={() =>
                    answer(invitation, false)
                  }
                >
                  Recusar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          Nenhum convite de viagem pendente.
        </p>
      )}
    </section>
  );
}