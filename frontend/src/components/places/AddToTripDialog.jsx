import { useState } from "react";

import Modal from "../Modal";
import { Button, ButtonLink } from "../ui";

import { pluralize } from "../../utils/places";
import { formatTripDate } from "../../utils/tripForm";

/*
  Escolha da viagem que vai receber os lugares selecionados.
  - onConfirm(trip): deve devolver uma Promise.
*/
export default function AddToTripDialog({
  open,
  count,
  trips,
  tripsError,
  onClose,
  onConfirm,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="small"
      title="Adicionar à viagem"
      description={`${pluralize(count, "lugar selecionado", "lugares selecionados")}. Escolha a viagem.`}
    >
      <TripChooser
        count={count}
        trips={trips}
        tripsError={tripsError}
        onCancel={onClose}
        onConfirm={onConfirm}
      />
    </Modal>
  );
}

function TripChooser({ count, trips, tripsError, onCancel, onConfirm }) {
  const [tripId, setTripId] = useState(
    trips.length === 1 ? trips[0].id : null,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (tripsError) {
    return (
      <p className="place-form-error" role="alert">
        Não foi possível carregar suas viagens. {tripsError}
      </p>
    );
  }

  if (trips.length === 0) {
    return (
      <div className="place-detail">
        <p className="muted">
          Você ainda não tem viagens em planejamento. Crie uma e volte para
          levar seus lugares.
        </p>

        <div className="modal-actions">
          <ButtonLink to="/viagens/nova">Planejar viagem</ButtonLink>
        </div>
      </div>
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const trip = trips.find((item) => item.id === tripId);
    if (!trip) {
      setError("Escolha uma viagem.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      await onConfirm(trip);
    } catch (failure) {
      setError(failure.message);
      setSaving(false);
    }
  }

  return (
    <form className="place-form" onSubmit={handleSubmit}>
      {error && (
        <p className="place-form-error" role="alert">
          {error}
        </p>
      )}

      <fieldset className="place-trip-options" disabled={saving}>
        <legend className="sr-only">Viagem</legend>

        {trips.map((trip) => (
          <label key={trip.id} className="place-trip-option">
            <input
              type="radio"
              name="trip"
              checked={tripId === trip.id}
              onChange={() => setTripId(trip.id)}
            />
            <span>
              <strong>{trip.title}</strong>
              <span className="muted">
                {" · "}
                {trip.destination || "Destino a decidir"}
                {" · "}
                {formatTripDate(trip.start_date)}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="modal-actions">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>

        <Button type="submit" disabled={saving || !tripId}>
          {saving
            ? "Adicionando…"
            : `Adicionar ${pluralize(count, "lugar", "lugares")}`}
        </Button>
      </div>
    </form>
  );
}
