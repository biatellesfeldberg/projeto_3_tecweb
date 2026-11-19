import { useEffect, useState } from "react";

import { Avatar, Badge, Button, Field } from "../ui";
import Feedback from "../Feedback";
import Modal from "../Modal";

import { listFriends } from "../../services/friends";
import { groupError } from "../../services/groups";

const name = (person) =>
  [person.first_name, person.last_name].filter(Boolean).join(" ") ||
  "Pessoa sem nome";

function Person({ person, children }) {
  return (
    <li className="group-person">
      <div className="group-identity">
        <span aria-hidden="true">
          <Avatar
            initials={
              `${person.first_name?.[0] || ""}${person.last_name?.[0] || ""}`.toUpperCase() ||
              "?"
            }
          />
        </span>

        <strong>{name(person)}</strong>
      </div>

      <div className="group-actions">{children}</div>
    </li>
  );
}

export default function GroupMembers({
  owner,
  members,
  isOwner,
  busy,
  expireSession,
  onInvite,
  onRemove,
  onLeave,
}) {
  const [target, setTarget] = useState(null);
  const [error, setError] = useState("");

  const accepted = members.filter(
    (member) => member.status === "accepted",
  );

  const pending = members.filter(
    (member) => member.status === "pending",
  );

  async function confirm() {
    setError("");

    const result = await (
      target === "leave"
        ? onLeave()
        : onRemove(target)
    );

    if (result.ok) {
      setTarget(null);
    } else {
      setError(result.error);
    }
  }

  return (
    <section
      className="card"
      aria-labelledby="group-members-title"
    >
      <div className="section-heading">
        <div>
          <h2 id="group-members-title">Integrantes</h2>

          <p className="muted">
            {accepted.length + 1} pessoa(s) no grupo ·{" "}
            {pending.length} convite(s) pendente(s)
          </p>
        </div>

        {!isOwner && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              setTarget("leave");
              setError("");
            }}
          >
            Sair do grupo
          </Button>
        )}
      </div>

      <ul
        className="group-people"
        aria-label="Integrantes da viagem"
      >
        <Person person={owner}>
          <Badge>Organizadora</Badge>
        </Person>

        {accepted.map((member) => (
          <Person
            key={member.id}
            person={member.user}
          >
            <Badge>Participante</Badge>

            {isOwner && (
              <Button
                variant="secondary"
                disabled={busy}
                aria-label={`Remover ${name(member.user)} do grupo`}
                onClick={() => {
                  setTarget(member);
                  setError("");
                }}
              >
                Remover integrante
              </Button>
            )}
          </Person>
        ))}
      </ul>

      <h3>Convites pendentes</h3>

      {pending.length ? (
        <ul
          className="group-people"
          aria-label="Convites pendentes"
        >
          {pending.map((member) => (
            <Person
              key={member.id}
              person={member.user}
            >
              <Badge>Aguardando resposta</Badge>

              {isOwner && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  aria-label={`Cancelar convite de ${name(member.user)}`}
                  onClick={() => {
                    setTarget(member);
                    setError("");
                  }}
                >
                  Cancelar convite
                </Button>
              )}
            </Person>
          ))}
        </ul>
      ) : (
        <p className="muted">Nenhum convite pendente.</p>
      )}

      {isOwner && (
        <InviteForm
          owner={owner}
          members={members}
          busy={busy}
          expireSession={expireSession}
          onInvite={onInvite}
        />
      )}

      <Modal
        open={Boolean(target)}
        title={
          target === "leave"
            ? "Sair do grupo"
            : target?.status === "pending"
              ? "Cancelar convite"
              : "Remover integrante"
        }
        onClose={() => {
          if (!busy) setTarget(null);
        }}
      >
        {target && (
          <>
            <p>
              {target === "leave"
                ? "Você precisará de outro convite para voltar. Suas respostas ao questionário serão removidas."
                : target.status === "pending"
                  ? `Cancelar o convite de ${name(target.user)}?`
                  : `Remover ${name(target.user)}? As respostas dessa pessoa ao questionário serão removidas.`}
            </p>

            {error && (
              <p role="alert" className="field-error">
                {error}
              </p>
            )}

            <div className="action-row">
              <Button
                variant="secondary"
                data-autofocus
                disabled={busy}
                onClick={() => setTarget(null)}
              >
                Voltar
              </Button>

              <Button
                className="group-danger"
                disabled={busy}
                onClick={confirm}
              >
                {busy ? "Salvando…" : "Confirmar"}
              </Button>
            </div>
          </>
        )}
      </Modal>
    </section>
  );
}

function InviteForm({
  owner,
  members,
  busy,
  expireSession,
  onInvite,
}) {
  const [friends, setFriends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setLoadError("");

    listFriends({ signal: controller.signal })
      .then((people) => {
        if (controller.signal.aborted) return;

        if (!Array.isArray(people)) {
          throw new Error(
            "Lista de amigos em formato inesperado.",
          );
        }

        setFriends(people);
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

  const available = friends.filter(
    (person) =>
      person.id !== owner.id &&
      !members.some(
        (member) => member.user.id === person.id,
      ),
  );

  async function submit(event) {
    event.preventDefault();
    setError("");

    if (
      busy ||
      !available.some(
        (person) => person.id === Number(selected),
      )
    ) {
      setError("Escolha uma pessoa disponível.");
      return;
    }

    const result = await onInvite(Number(selected));

    if (result.ok) {
      setSelected("");
    } else {
      setError(result.error);
    }
  }

  return (
    <div className="group-invite-form">
      <h3>Convidar amigos</h3>

      {loading ? (
        <Feedback
          kind="loading"
          title="Carregando amigos…"
        />
      ) : loadError ? (
        <Feedback
          kind="error"
          title="Não foi possível carregar seus amigos."
          detail={loadError}
          onRetry={() => setRetry((value) => value + 1)}
        />
      ) : (
        <>
          {available.length ? (
            <form
              onSubmit={submit}
              className="group-form"
            >
              <Field
                id="group-friend"
                label="Amigo para convidar"
                error={error}
              >
                <select
                  id="group-friend"
                  value={selected}
                  onChange={(event) =>
                    setSelected(event.target.value)
                  }
                  disabled={busy}
                  aria-invalid={Boolean(error)}
                  aria-describedby={
                    error
                      ? "group-friend-error"
                      : undefined
                  }
                >
                  <option value="">
                    Selecione uma pessoa
                  </option>

                  {available.map((person) => (
                    <option
                      key={person.id}
                      value={person.id}
                    >
                      {name(person)}
                    </option>
                  ))}
                </select>
              </Field>

              <Button
                type="submit"
                disabled={busy || !selected}
              >
                Enviar convite
              </Button>
            </form>
          ) : (
            <p className="muted">
              Não há amigos disponíveis para convidar.
              Adicione amigos na página Amigos ou aguarde
              os convites enviados.
            </p>
          )}

          <Button
            variant="ghost"
            disabled={busy}
            onClick={() =>
              setRetry((value) => value + 1)
            }
          >
            Atualizar amigos disponíveis
          </Button>
        </>
      )}
    </div>
  );
}