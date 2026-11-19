import { useEffect, useState } from "react";

import { Badge, Button, Field } from "../ui";
import Modal from "../Modal";

const categories = {
  destination: "Destino",
  restaurant: "Restaurante",
  activity: "Atividade",
};

export default function PollCard({
  poll,
  isOwner,
  busy,
  owner,
  onVote,
  onClose,
  onRefresh,
}) {
  const [choice, setChoice] = useState(
    String(poll.my_vote || ""),
  );
  const [error, setError] = useState("");
  const [closing, setClosing] = useState(false);

  const closed = poll.status === "closed";

  useEffect(() => {
    setChoice(String(poll.my_vote || ""));
  }, [poll.my_vote]);

  useEffect(() => {
    if (closed) setClosing(false);
  }, [closed]);

  async function vote(event) {
    event.preventDefault();
    setError("");

    if (busy) return;

    if (
      !poll.options.some(
        (option) => option.id === Number(choice),
      )
    ) {
      setError("Escolha uma opção antes de votar.");
      return;
    }

    const result = await onVote(
      poll.id,
      Number(choice),
    );

    if (!result.ok) {
      setError(result.error);
    }
  }

  async function refresh() {
    setError("");

    const result = await onRefresh(poll.id);

    if (!result.ok) {
      setError(result.error);
    }

    return result;
  }

  async function beginClose() {
    const result = await refresh();

    if (
      result.ok &&
      result.data.status === "open"
    ) {
      setClosing(true);
    }
  }

  return (
    <article
      className="card group-poll"
      aria-labelledby={`poll-heading-${poll.id}`}
    >
      <div className="group-actions">
        <Badge>
          {categories[poll.category] || poll.category}
        </Badge>

        <Badge>
          {closed ? "Encerrada" : "Aberta"}
        </Badge>
      </div>

      <h3 id={`poll-heading-${poll.id}`}>
        {poll.title}
      </h3>

      <p className="muted">
        {poll.total_votes} voto(s) registrado(s)
      </p>

      <ul
        className="group-results"
        aria-label={`Resultados de ${poll.title}`}
      >
        {poll.options.map((option) => (
          <li key={option.id}>
            <div>
              <span>
                {option.label}
                {poll.my_vote === option.id
                  ? " · Seu voto"
                  : ""}
              </span>

              <strong>
                {option.votes} voto(s)
              </strong>
            </div>

            <progress
              value={option.votes}
              max={Math.max(poll.total_votes, 1)}
              aria-label={`Votos em ${option.label}`}
            />
          </li>
        ))}
      </ul>

      {closed ? (
        <div className="group-decision">
          <h4>
            Decisão:{" "}
            {poll.decision?.label || "Não informada"}
          </h4>

          <p>{poll.decision?.reason}</p>

          <p className="muted">
            Registrada por{" "}
            {[owner.first_name, owner.last_name]
              .filter(Boolean)
              .join(" ")}
            {poll.closed_at
              ? ` em ${new Date(
                  poll.closed_at,
                ).toLocaleString("pt-BR")}`
              : ""}
            .
          </p>
        </div>
      ) : (
        <form
          className="group-vote"
          onSubmit={vote}
        >
          <fieldset disabled={busy}>
            <legend>Seu voto</legend>

            {poll.options.map((option) => (
              <label
                className="group-radio"
                key={option.id}
              >
                <input
                  type="radio"
                  name={`poll-${poll.id}`}
                  value={option.id}
                  checked={
                    choice === String(option.id)
                  }
                  onChange={(event) =>
                    setChoice(event.target.value)
                  }
                />

                {option.label}
              </label>
            ))}
          </fieldset>

          <Button
            type="submit"
            disabled={
              busy ||
              !choice ||
              choice === String(poll.my_vote || "")
            }
          >
            {poll.my_vote
              ? "Alterar voto"
              : "Salvar voto"}
          </Button>
        </form>
      )}

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}

      <div className="group-actions">
        <Button
          variant="ghost"
          disabled={busy}
          onClick={refresh}
        >
          Atualizar resultados
        </Button>

        {isOwner && !closed && (
          <Button
            variant="secondary"
            disabled={
              busy || poll.total_votes === 0
            }
            onClick={beginClose}
          >
            Encerrar votação
          </Button>
        )}
      </div>

      {isOwner &&
        !closed &&
        poll.total_votes === 0 && (
          <p className="muted">
            É necessário pelo menos um voto para encerrar.
          </p>
        )}

      <Modal
        open={closing}
        title={`Encerrar: ${poll.title}`}
        onClose={() => {
          if (!busy) setClosing(false);
        }}
      >
        <ClosePollForm
          poll={poll}
          busy={busy}
          onRefresh={refresh}
          onClose={onClose}
          onCancel={() => setClosing(false)}
        />
      </Modal>
    </article>
  );
}

function ClosePollForm({
  poll,
  busy,
  onRefresh,
  onClose,
  onCancel,
}) {
  const [choice, setChoice] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const maximum = Math.max(
    0,
    ...poll.options.map(
      (option) => option.votes,
    ),
  );

  const leaders = poll.options.filter(
    (option) => option.votes === maximum,
  );

  async function submit(event) {
    event.preventDefault();
    setError("");

    if (busy) return;

    if (
      !poll.total_votes ||
      !leaders.some(
        (option) => option.id === Number(choice),
      )
    ) {
      setError(
        "Escolha uma opção que esteja na liderança.",
      );
      return;
    }

    if (!reason.trim()) {
      setError(
        "Explique a decisão antes de encerrar.",
      );
      return;
    }

    const result = await onClose(poll.id, {
      option_id: Number(choice),
      reason: reason.trim(),
    });

    if (result.ok) {
      onCancel();
    } else {
      setError(result.error);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="group-form"
    >
      <p>
        {leaders.length > 1
          ? "Há um empate. Escolha uma das opções na liderança e explique a decisão."
          : "Confirme a opção mais votada e explique a decisão."}
      </p>

      <Field
        id={`close-choice-${poll.id}`}
        label="Opção escolhida"
      >
        <select
          id={`close-choice-${poll.id}`}
          value={choice}
          onChange={(event) =>
            setChoice(event.target.value)
          }
          disabled={busy}
          data-autofocus
        >
          <option value="">
            Selecione uma opção
          </option>

          {leaders.map((option) => (
            <option
              key={option.id}
              value={option.id}
            >
              {option.label} ({option.votes} voto(s))
            </option>
          ))}
        </select>
      </Field>

      <Field
        id={`close-reason-${poll.id}`}
        label="Justificativa"
      >
        <textarea
          id={`close-reason-${poll.id}`}
          value={reason}
          maxLength={500}
          rows={3}
          onChange={(event) =>
            setReason(event.target.value)
          }
          disabled={busy}
        />
      </Field>

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}

      <div className="action-row">
        <Button
          variant="secondary"
          disabled={busy}
          onClick={onCancel}
        >
          Voltar
        </Button>

        <Button
          variant="ghost"
          disabled={busy}
          onClick={async () => {
            const result = await onRefresh();

            if (!result.ok) {
              setError(result.error);
            }
          }}
        >
          Atualizar votos
        </Button>

        <Button
          type="submit"
          disabled={busy}
        >
          {busy
            ? "Encerrando…"
            : "Registrar decisão"}
        </Button>
      </div>
    </form>
  );
}