import { useState } from "react";

import Modal from "../Modal";
import { Button, Field } from "../ui";

import { placeCategories } from "../../utils/places";
import {
  activityPayload,
  activityToForm,
  costTypes,
  emptyActivityForm,
  formatDayLong,
  placeToActivityForm,
  validateActivity,
} from "../../utils/itinerary";

/*
  Cadastro e edição de uma atividade do roteiro.
  - activity: atividade sendo editada (ou null para cadastrar).
  - initial: valores iniciais de um cadastro (ex.: vindos de um lugar salvo).
  - places: lugares salvos da viagem, para preencher o formulário.
  - onSave(payload): Promise; erros por campo da API aparecem no formulário.
*/
export default function ActivityFormDialog({
  open,
  activity,
  initial,
  days,
  places = [],
  currency,
  onClose,
  onSave,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="large"
      title={activity ? "Editar atividade" : "Adicionar atividade"}
      description={
        activity
          ? "Ajuste horário, local, custo ou mova para outro dia."
          : "Inclua no roteiro algo que a IA não sugeriu."
      }
    >
      <ActivityForm
        activity={activity}
        initial={initial}
        days={days}
        places={places}
        currency={currency}
        onCancel={onClose}
        onSave={onSave}
      />
    </Modal>
  );
}

function ActivityForm({
  activity,
  initial,
  days,
  places,
  currency,
  onCancel,
  onSave,
}) {
  const [form, setForm] = useState(() =>
    activity ? activityToForm(activity) : { ...emptyActivityForm(), ...initial },
  );
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function fillFromPlace(placeId) {
    const place = places.find((item) => String(item.id) === placeId);
    if (!place) return;
    setForm((current) => placeToActivityForm(place, current.day));
    setErrors({});
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const found = validateActivity(form);
    setErrors(found);
    setFormError("");

    if (Object.keys(found).length > 0) {
      document.getElementById(`activity-${Object.keys(found)[0]}`)?.focus();
      return;
    }

    setSaving(true);

    try {
      await onSave(activityPayload(form));
    } catch (failure) {
      const fields = failure.fields || {};
      const fieldErrors = {};

      for (const key of Object.keys(emptyActivityForm())) {
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
      id: `activity-${field}`,
      name: field,
      value: form[field],
      onChange: (event) => update(field, event.target.value),
      "aria-invalid": errors[field] ? "true" : undefined,
      "aria-describedby": errors[field]
        ? `activity-${field}-error`
        : undefined,
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
        {!activity && places.length > 0 && (
          <Field
            id="activity-place"
            label="Começar a partir de um lugar salvo"
            hint="Preenche nome, local, coordenadas e observações."
          >
            <select
              id="activity-place"
              defaultValue=""
              onChange={(event) => fillFromPlace(event.target.value)}
            >
              <option value="">Escolha um lugar da viagem…</option>
              {places.map((place) => (
                <option key={place.id} value={place.id}>
                  {place.name}
                  {place.city ? ` · ${place.city}` : ""}
                </option>
              ))}
            </select>
          </Field>
        )}

        <div className="place-form-row">
          <Field id="activity-title" label="Atividade *" error={errors.title}>
            <input
              {...inputProps("title")}
              maxLength={150}
              placeholder="Ex.: Café e uma volta pela Baixa"
              data-autofocus
              required
            />
          </Field>

          <Field id="activity-day" label="Dia *" error={errors.day}>
            <select {...inputProps("day")}>
              <option value="">Escolha o dia</option>
              {days.map((day) => (
                <option key={day.id} value={day.id}>
                  Dia {day.day_number} · {formatDayLong(day.date)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="activity-form-times">
          <Field id="activity-start_time" label="Início" error={errors.start_time}>
            <input {...inputProps("start_time")} type="time" />
          </Field>

          <Field id="activity-end_time" label="Término" error={errors.end_time}>
            <input {...inputProps("end_time")} type="time" />
          </Field>

          <Field
            id="activity-duration_minutes"
            label="Duração (min)"
            error={errors.duration_minutes}
          >
            <input
              {...inputProps("duration_minutes")}
              inputMode="numeric"
              placeholder="Ex.: 90"
            />
          </Field>

          <Field id="activity-category" label="Categoria" error={errors.category}>
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
          <Field
            id="activity-location_name"
            label="Local"
            error={errors.location_name}
          >
            <input
              {...inputProps("location_name")}
              maxLength={150}
              placeholder="Ex.: Miradouro de Santa Luzia"
            />
          </Field>

          <Field id="activity-address" label="Endereço" error={errors.address}>
            <input {...inputProps("address")} maxLength={255} />
          </Field>
        </div>

        <div className="place-form-row">
          <Field
            id="activity-estimated_cost"
            label={`Custo estimado (${currency})`}
            error={errors.estimated_cost}
          >
            <input
              {...inputProps("estimated_cost")}
              inputMode="decimal"
              placeholder="0,00"
            />
          </Field>

          <Field id="activity-cost_type" label="O custo é" error={errors.cost_type}>
            <select {...inputProps("cost_type")}>
              {costTypes.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field
          id="activity-description"
          label="Descrição"
          error={errors.description}
        >
          <textarea {...inputProps("description")} rows={2} />
        </Field>

        <Field
          id="activity-notes"
          label="Observações"
          hint="Reserva, ingresso, o que levar…"
          error={errors.notes}
        >
          <textarea {...inputProps("notes")} rows={2} />
        </Field>

        <fieldset className="place-form-group">
          <legend>Localização no mapa (opcional)</legend>
          <p className="muted">
            Sem coordenadas, a atividade continua na lista, mas não aparece no
            mapa. No Google Maps, clique com o botão direito no lugar e copie
            os números.
          </p>

          <div className="place-form-row">
            <Field id="activity-latitude" label="Latitude" error={errors.latitude}>
              <input
                {...inputProps("latitude")}
                inputMode="decimal"
                placeholder="Ex.: 38.7117"
              />
            </Field>

            <Field
              id="activity-longitude"
              label="Longitude"
              error={errors.longitude}
            >
              <input
                {...inputProps("longitude")}
                inputMode="decimal"
                placeholder="Ex.: -9.1302"
              />
            </Field>
          </div>
        </fieldset>

        <Field
          id="activity-image_url"
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
      </fieldset>

      <div className="modal-actions">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>

        <Button type="submit" disabled={saving}>
          {saving
            ? "Salvando…"
            : activity
              ? "Salvar alterações"
              : "Adicionar atividade"}
        </Button>
      </div>
    </form>
  );
}
