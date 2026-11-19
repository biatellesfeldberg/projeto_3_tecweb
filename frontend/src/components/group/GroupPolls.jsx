import { useState } from "react";

import { Button, Field } from "../ui";
import Feedback from "../Feedback";
import Modal from "../Modal";
import PollCard from "./PollCard";

export default function GroupPolls({
  polls,
  isOwner,
  busy,
  owner,
  onCreate,
  onVote,
  onClose,
  onRefresh,
}) {
  const [creating, setCreating] = useState(false);

  const opened = polls.filter(
    (poll) => poll.status === "open",
  );

  const closed = polls.filter(
    (poll) => poll.status === "closed",
  );

  const card = (poll) => (
    <PollCard
      key={poll.id}
      poll={poll}
      isOwner={isOwner}
      busy={busy}
      owner={owner}
      onVote={onVote}
      onClose={onClose}
      onRefresh={onRefresh}
    />
  );

  return (
    <>
      <section aria-labelledby="group-polls-title">
        <div className="section-heading">
          <h2 id="group-polls-title">
            Votações abertas
          </h2>

          {isOwner && (
            <Button
              disabled={busy}
              onClick={() => setCreating(true)}
            >
              + Criar votação
            </Button>
          )}
        </div>

        {opened.length ? (
          <div className="group-polls">
            {opened.map(card)}
          </div>
        ) : (
          <Feedback
            kind="empty"
            title="Nenhuma votação aberta."
            detail={
              isOwner
                ? "Crie uma votação para decidir com o grupo."
                : "A organizadora pode criar uma votação para o grupo."
            }
          />
        )}
      </section>

      <section aria-labelledby="group-decisions-title">
        <div className="section-heading">
          <h2 id="group-decisions-title">
            Decisões do grupo
          </h2>
        </div>

        {closed.length ? (
          <div className="group-polls">
            {closed.map(card)}
          </div>
        ) : (
          <Feedback
            kind="empty"
            title="Nenhuma decisão registrada."
            detail="As votações encerradas aparecerão aqui com o resultado e a justificativa."
          />
        )}
      </section>

      <Modal
        open={creating}
        title="Criar votação"
        onClose={() => {
          if (!busy) setCreating(false);
        }}
      >
        <CreatePollForm
          busy={busy}
          onCreate={onCreate}
          onDone={() => setCreating(false)}
        />
      </Modal>
    </>
  );
}

function CreatePollForm({
  busy,
  onCreate,
  onDone,
}) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("destination");
  const [options, setOptions] = useState("");
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();

    if (busy) return;

    const labels = options
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean);

    const validation = {};

    if (!title.trim()) {
      validation.title = "Informe o título.";
    }

    if (labels.length < 2 || labels.length > 10) {
      validation.options =
        "Informe entre 2 e 10 opções, uma por linha.";
    } else if (
      labels.some((label) => label.length > 150)
    ) {
      validation.options =
        "Cada opção pode ter até 150 caracteres.";
    } else if (
      new Set(
        labels.map((label) =>
          label.toLocaleLowerCase(),
        ),
      ).size !== labels.length
    ) {
      validation.options =
        "As opções não podem se repetir.";
    }

    setErrors(validation);
    setError("");

    if (Object.keys(validation).length) return;

    const result = await onCreate({
      title: title.trim(),
      category,
      options: labels,
    });

    if (result.ok) {
      onDone();
    } else {
      setError(result.error);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="group-form"
    >
      <Field
        id="poll-title"
        label="Título da votação"
        error={errors.title}
      >
        <input
          id="poll-title"
          data-autofocus
          maxLength={150}
          value={title}
          onChange={(event) =>
            setTitle(event.target.value)
          }
          disabled={busy}
          aria-invalid={Boolean(errors.title)}
          aria-describedby={
            errors.title
              ? "poll-title-error"
              : undefined
          }
        />
      </Field>

      <Field
        id="poll-category"
        label="Categoria"
      >
        <select
          id="poll-category"
          value={category}
          onChange={(event) =>
            setCategory(event.target.value)
          }
          disabled={busy}
        >
          <option value="destination">
            Destino
          </option>
          <option value="restaurant">
            Restaurante
          </option>
          <option value="activity">
            Atividade
          </option>
        </select>
      </Field>

      <Field
        id="poll-options"
        label="Opções"
        hint="Uma opção por linha. Mínimo de 2 e máximo de 10."
        error={errors.options}
      >
        <textarea
          id="poll-options"
          rows={5}
          value={options}
          onChange={(event) =>
            setOptions(event.target.value)
          }
          disabled={busy}
          aria-invalid={Boolean(errors.options)}
          aria-describedby={
            `poll-options-hint${
              errors.options
                ? " poll-options-error"
                : ""
            }`
          }
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
          onClick={onDone}
        >
          Cancelar
        </Button>

        <Button
          type="submit"
          disabled={busy}
        >
          {busy ? "Criando…" : "Criar votação"}
        </Button>
      </div>
    </form>
  );
}