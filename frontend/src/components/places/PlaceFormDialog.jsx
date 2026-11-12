import { useState } from "react";

import Modal from "../Modal";
import { Button, Field } from "../ui";

import {
  emptyPlaceForm,
  placeCategories,
  placePayload,
  placeToForm,
  validatePlace,
} from "../../utils/places";
import { formatTripDate } from "../../utils/tripForm";

/*
  Cadastro e edição de um lugar.
  - place: lugar sendo editado (ou null para cadastrar).
  - trips: viagens que podem receber o lugar.
  - onSave(payload): deve devolver uma Promise; se lançar ApiError, os erros
    por campo aparecem no formulário.
*/
export default function PlaceFormDialog({
  open,
  place,
  trips,
  initialTripIds = [],
  onClose,
  onSave,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="large"
      title={place ? "Editar lugar" : "Adicionar lugar"}
      description={
        place
          ? "Atualize as informações e as viagens deste lugar."
          : "O café que te indicaram, a praia que você quer conhecer, a próxima descoberta."
      }
    >
      <PlaceForm
        place={place}
        trips={trips}
        initialTripIds={initialTripIds}
        onCancel={onClose}
        onSave={onSave}
      />
    </Modal>
  );
}

function PlaceForm({ place, trips, initialTripIds, onCancel, onSave }) {
  const [form, setForm] = useState(() =>
    place
      ? placeToForm(place)
      : { ...emptyPlaceForm(), trip_ids: initialTripIds },
  );
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // Viagens disponíveis mais as que o lugar já tem (mesmo que realizadas).
  const tripOptions = [...trips];
  for (const trip of place?.trips || []) {
    if (!tripOptions.some((item) => item.id === trip.id)) {
      tripOptions.push(trip);
    }
  }

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function toggleTrip(tripId) {
    setForm((current) => ({
      ...current,
      trip_ids: current.trip_ids.includes(tripId)
        ? current.trip_ids.filter((id) => id !== tripId)
        : [...current.trip_ids, tripId],
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const found = validatePlace(form);
    setErrors(found);
    setFormError("");

    if (Object.keys(found).length > 0) {
      const first = Object.keys(found)[0];
      document.getElementById(`place-${first}`)?.focus();
      return;
    }

    setSaving(true);

    try {
      await onSave(placePayload(form));
    } catch (failure) {
      const fields = failure.fields || {};
      const fieldErrors = {};

      for (const key of Object.keys(emptyPlaceForm())) {
        if (fields[key]) fieldErrors[key] = fields[key];
      }

      setErrors(fieldErrors);
      setFormError(
        Object.keys(fieldErrors).length > 0
          ? "Confira os campos destacados."
          : failure.message,
      );
      setSaving(false);
    }
  }

  function inputProps(field) {
    return {
      id: `place-${field}`,
      name: field,
      value: form[field],
      onChange: (event) => update(field, event.target.value),
      "aria-invalid": errors[field] ? "true" : undefined,
      "aria-describedby": errors[field] ? `place-${field}-error` : undefined,
    };
  }

  return (
    <form className="place-form" onSubmit={handleSubmit} noValidate>
      {formError && (
        <p className="place-form-error" role="alert">
          {formError}
        </p>
      )}

      <fieldset className="place-form-fields" disabled={saving}>
        <div className="place-form-row">
          <Field id="place-name" label="Nome *" error={errors.name}>
            <input
              {...inputProps("name")}
              maxLength={150}
              placeholder="Ex.: Um café em Alfama"
              data-autofocus
              required
            />
          </Field>

          <Field id="place-category" label="Categoria" error={errors.category}>
            <select {...inputProps("category")}>
              {placeCategories.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="place-form-row">
          <Field id="place-city" label="Cidade" error={errors.city}>
            <input
              {...inputProps("city")}
              maxLength={120}
              placeholder="Ex.: Lisboa"
            />
          </Field>

          <Field id="place-country" label="País" error={errors.country}>
            <input
              {...inputProps("country")}
              maxLength={120}
              placeholder="Ex.: Portugal"
            />
          </Field>
        </div>

        <Field id="place-address" label="Endereço" error={errors.address}>
          <input {...inputProps("address")} maxLength={255} />
        </Field>

        <Field
          id="place-description"
          label="Descrição"
          error={errors.description}
        >
          <textarea {...inputProps("description")} rows={3} />
        </Field>

        <Field
          id="place-notes"
          label="Observações"
          hint="Quem indicou, melhor horário, o que pedir…"
          error={errors.notes}
        >
          <textarea {...inputProps("notes")} rows={3} />
        </Field>

        <Field
          id="place-image_url"
          label="Link de uma imagem"
          error={errors.image_url}
        >
          <input
            {...inputProps("image_url")}
            type="url"
            inputMode="url"
            placeholder="https://"
          />
        </Field>

        <fieldset className="place-form-group">
          <legend>Localização no mapa (opcional)</legend>
          <p className="muted">
            No Google Maps, clique com o botão direito no lugar e copie os
            números. O primeiro é a latitude e o segundo, a longitude.
          </p>

          <div className="place-form-row">
            <Field id="place-latitude" label="Latitude" error={errors.latitude}>
              <input
                {...inputProps("latitude")}
                inputMode="decimal"
                placeholder="Ex.: 38.7114"
              />
            </Field>

            <Field
              id="place-longitude"
              label="Longitude"
              error={errors.longitude}
            >
              <input
                {...inputProps("longitude")}
                inputMode="decimal"
                placeholder="Ex.: -9.1300"
              />
            </Field>
          </div>
        </fieldset>

        <fieldset className="place-form-group">
          <legend>Viagens</legend>

          {tripOptions.length === 0 ? (
            <p className="muted">
              Você ainda não tem viagens em planejamento. O lugar fica
              guardado na sua coleção.
            </p>
          ) : (
            <div className="place-trip-options">
              {tripOptions.map((trip) => (
                <label key={trip.id} className="place-trip-option">
                  <input
                    type="checkbox"
                    checked={form.trip_ids.includes(trip.id)}
                    onChange={() => toggleTrip(trip.id)}
                  />
                  <span>
                    <strong>{trip.title}</strong>
                    {trip.start_date && (
                      <span className="muted">
                        {" · "}
                        {formatTripDate(trip.start_date)}
                      </span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          )}

          {errors.trip_ids && (
            <p className="field-error" role="alert">
              {errors.trip_ids}
            </p>
          )}
        </fieldset>
      </fieldset>

      <div className="modal-actions">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>

        <Button type="submit" disabled={saving}>
          {saving
            ? "Salvando…"
            : place
              ? "Salvar alterações"
              : "Adicionar lugar"}
        </Button>
      </div>
    </form>
  );
}
