import { useState } from "react";

import { Button, Field } from "../ui";

/*
  Título e notas do dia ("Notas do dia").
  - onSave({ title, notes }): Promise.
  O componente deve receber key={day.id} para reiniciar ao trocar de dia.
*/
export default function DayNotes({ day, onSave }) {
  const [title, setTitle] = useState(day.title);
  const [notes, setNotes] = useState(day.notes);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  const changed = title.trim() !== day.title || notes.trim() !== day.notes;

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("saving");
    setError("");

    try {
      await onSave({ title: title.trim(), notes: notes.trim() });
      setStatus("saved");
    } catch (failure) {
      setError(failure.message);
      setStatus("idle");
    }
  }

  return (
    <form className="day-notes" onSubmit={handleSubmit}>
      <h3>Notas do dia</h3>

      <fieldset className="place-form-fields" disabled={status === "saving"}>
        <Field id={`day-title-${day.id}`} label="Título do dia">
          <input
            id={`day-title-${day.id}`}
            value={title}
            maxLength={120}
            placeholder="Ex.: Baixa e Alfama"
            onChange={(event) => {
              setTitle(event.target.value);
              setStatus("idle");
            }}
          />
        </Field>

        <Field id={`day-notes-${day.id}`} label="Notas">
          <textarea
            id={`day-notes-${day.id}`}
            value={notes}
            rows={3}
            placeholder="Levar casaco, reservar o jantar…"
            onChange={(event) => {
              setNotes(event.target.value);
              setStatus("idle");
            }}
          />
        </Field>
      </fieldset>

      <div className="day-notes-actions">
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
        {status === "saved" && !changed && (
          <p className="day-notes-saved" role="status">
            ✓ Notas salvas
          </p>
        )}
        <Button
          type="submit"
          variant="secondary"
          disabled={!changed || status === "saving"}
        >
          {status === "saving" ? "Salvando…" : "Salvar notas"}
        </Button>
      </div>
    </form>
  );
}
