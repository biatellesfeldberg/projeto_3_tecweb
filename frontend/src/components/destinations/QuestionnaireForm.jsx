import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Button,
  Card,
  Field,
} from "../ui";

import Feedback from "../Feedback";

import {
  saveMyQuestionnaire,
} from "../../services/groupDestinations";

import {
  travelInterests,
} from "../../utils/tripForm";

import {
  initialQuestionnaire,
  questionnairePayload,
  questionnaireSelects,
} from "../../utils/questionnaire";

export default function QuestionnaireForm({
  trip,
  answers,
  disabled,
  onDirty,
  onSaved,
  onFailure,
}) {
  const [form, setForm] = useState(
    () => initialQuestionnaire(answers, trip),
  );

  const [baseline, setBaseline] = useState(
    () =>
      JSON.stringify(
        initialQuestionnaire(answers, trip),
      ),
  );

  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  const controllerRef = useRef(null);
  const formRef = useRef(null);

  useEffect(
    () => () => controllerRef.current?.abort(),
    [],
  );

  useEffect(() => {
    onDirty(
      JSON.stringify(form) !== baseline ||
        pending,
    );
  }, [
    form,
    baseline,
    pending,
    onDirty,
  ]);

  useEffect(() => {
    formRef.current
      ?.querySelector('[aria-invalid="true"]')
      ?.focus();
  }, [errors]);

  function change(key, value) {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));

    setErrors((current) => ({
      ...current,
      [key]: "",
    }));

    setMessage("");
    setSaved(false);
  }

  async function submit(event) {
    event.preventDefault();

    if (
      controllerRef.current ||
      disabled
    ) {
      return;
    }

    const {
      payload,
      errors: nextErrors,
    } = questionnairePayload(form);

    setErrors(nextErrors);
    setMessage("");
    setSaved(false);

    if (
      Object.keys(nextErrors).length
    ) {
      return;
    }

    const controller = new AbortController();

    controllerRef.current = controller;
    setPending(true);

    try {
      const data = await saveMyQuestionnaire(
        trip.id,
        payload,
        { signal: controller.signal },
      );

      if (controller.signal.aborted) {
        return;
      }

      const next = initialQuestionnaire(
        data.answers,
        trip,
      );

      setForm(next);
      setBaseline(JSON.stringify(next));
      setSaved(true);

      onSaved();
    } catch (failure) {
      if (controller.signal.aborted) {
        return;
      }

      onFailure(failure);
      setErrors(failure.fields || {});
      setMessage(failure.message);
    } finally {
      if (!controller.signal.aborted) {
        controllerRef.current = null;
        setPending(false);
      }
    }
  }

  const attrs = (key) => ({
    id: `question-${key}`,
    name: key,
    value: form[key],
    onChange: (event) =>
      change(key, event.target.value),
    "aria-invalid": Boolean(errors[key]),
    "aria-describedby": errors[key]
      ? `question-${key}-error`
      : undefined,
  });

  const field = (
    key,
    label,
    control,
  ) => (
    <Field
      key={key}
      id={`question-${key}`}
      label={label}
      error={errors[key]}
    >
      {control}
    </Field>
  );

  return (
    <Card>
      <h2>Seu questionário</h2>

      <p className="muted">
        Cada pessoa responde por si. O grupo verá sua
        nota de compatibilidade; seus campos individuais
        não são exibidos nesta tela.
      </p>

      <form
        ref={formRef}
        onSubmit={submit}
        noValidate
      >
        <fieldset
          className="destination-fields"
          disabled={pending || disabled}
        >
          <legend className="sr-only">
            Suas preferências para esta viagem
          </legend>

          <div className="destination-form-grid">
            {field(
              "max_budget",
              `Orçamento por pessoa, para toda a viagem (${trip.currency})`,
              <input
                {...attrs("max_budget")}
                inputMode="decimal"
                placeholder="Ex.: 2500,00"
              />,
            )}

            {field(
              "days",
              "Duração desejada em dias",
              <input
                {...attrs("days")}
                type="number"
                min="1"
                max="60"
                step="1"
              />,
            )}

            {questionnaireSelects.map(
              ([key, label, options]) =>
                field(
                  key,
                  label,
                  <select {...attrs(key)}>
                    <option value="">
                      Selecione
                    </option>

                    {options.map(
                      ([value, text]) => (
                        <option
                          key={value}
                          value={value}
                        >
                          {text}
                        </option>
                      ),
                    )}
                  </select>,
                ),
            )}
          </div>

          <fieldset
            className="destination-interests"
            aria-describedby={
              errors.interests
                ? "interests-error"
                : undefined
            }
          >
            <legend>Interesses</legend>

            <div>
              {travelInterests.map(
                ([value, label]) => (
                  <label key={value}>
                    <input
                      type="checkbox"
                      checked={form.interests.includes(
                        value,
                      )}
                      aria-invalid={Boolean(
                        errors.interests,
                      )}
                      onChange={(event) =>
                        change(
                          "interests",
                          event.target.checked
                            ? [
                                ...form.interests,
                                value,
                              ]
                            : form.interests.filter(
                                (item) =>
                                  item !== value,
                              ),
                        )
                      }
                    />

                    {" "}
                    {label}
                  </label>
                ),
              )}
            </div>

            {errors.interests && (
              <p
                className="field-error"
                id="interests-error"
                role="alert"
              >
                {errors.interests}
              </p>
            )}
          </fieldset>

          {field(
            "avoided_destinations",
            "Destinos que você prefere evitar — um por linha",
            <textarea
              {...attrs("avoided_destinations")}
              rows="3"
            />,
          )}

          {field(
            "notes",
            "Outras preferências",
            <textarea
              {...attrs("notes")}
              rows="3"
              maxLength="500"
            />,
          )}

          <p className="muted">
            As preferências e observações podem ser
            enviadas ao Gemini para analisar o grupo.
            Inclua somente informações necessárias
            à viagem.
          </p>

          <Button
            type="submit"
            disabled={pending || disabled}
          >
            {pending
              ? "Salvando respostas…"
              : "Salvar respostas"}
          </Button>
        </fieldset>

        {saved && (
          <Feedback
            kind="success"
            title="Respostas salvas."
            detail="O progresso do grupo foi atualizado."
          />
        )}

        {message && (
          <Feedback
            kind="error"
            title="Não foi possível salvar suas respostas."
            detail={message}
            onRetry={() =>
              formRef.current?.requestSubmit()
            }
            busy={pending || disabled}
          />
        )}
      </form>
    </Card>
  );
}