import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Navigate,
  useNavigate,
} from "react-router-dom";

import {
  Button,
  ButtonLink,
  Card,
  Field,
  PageHeading,
} from "../components/ui";

import { useAuth } from "../contexts/AuthContext";
import { createTrip } from "../services/trips";

import {
  initialTrip,
  transports,
  travelInterests,
  travelPaces,
  travelStyles,
  tripPayload,
  validateTrip,
} from "../utils/tripForm";

import "./trips.css";

export default function NewTripPage() {
  const {
    user,
    isRestoring,
    token,
    accountRequest,
    expireSession,
  } = useAuth();

  const userId = user?.id;
  const navigate = useNavigate();

  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retry, setRetry] = useState(0);

  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  const formRef = useRef(null);
  const messageRef = useRef(null);
  const requestRef = useRef(null);

  useEffect(() => {
    if (!userId) {
      return;
    }

    const controller = new AbortController();

    setLoading(true);
    setLoadError("");

    accountRequest("me", {
      signal: controller.signal,
    })
      .then((profile) => {
        setForm(initialTrip(profile));
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setLoadError(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [userId, accountRequest, retry]);

  useEffect(() => {
    return () => requestRef.current?.abort();
  }, []);

  useEffect(() => {
    if (message) {
      messageRef.current?.focus();
    } else {
      formRef.current
        ?.querySelector('[aria-invalid="true"]')
        ?.focus();
    }
  }, [errors, message]);

  function change(event) {
    const {
      name,
      value,
      checked,
      type,
    } = event.target;

    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
          : value,
    }));

    setErrors((current) => ({
      ...current,
      [name]: "",

      ...(name === "undecided"
        ? { destination: "" }
        : {}),
    }));

    setMessage("");
  }

  async function submit(event) {
    event.preventDefault();

    if (requestRef.current) {
      return;
    }

    const nextErrors = validateTrip(form);

    setErrors(nextErrors);
    setMessage("");

    if (Object.keys(nextErrors).length) {
      return;
    }

    const controller = new AbortController();

    requestRef.current = controller;
    setPending(true);

    try {
      const created = await createTrip(
        tripPayload(form),
        {
          token,
          signal: controller.signal,
        },
      );

      if (controller.signal.aborted) {
        return;
      }

      if (!created?.id) {
        throw new Error(
          "Não foi possível confirmar a criação. Confira Minhas viagens antes de tentar novamente.",
        );
      }

      navigate("/viagens?status=planning", {
        replace: true,
        state: {
          createdTripId: created.id,
        },
      });
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      if (error.status === 401) {
        expireSession();
        return;
      }

      setErrors(error.fields || {});

      setMessage(
        error.status === 0
          ? "Não foi possível confirmar a criação. Confira Minhas viagens antes de tentar novamente."
          : error.message,
      );
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
      }

      if (!controller.signal.aborted) {
        setPending(false);
      }
    }
  }

  if (isRestoring) {
    return (
      <p role="status">
        Verificando sua sessão…
      </p>
    );
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  if (loading) {
    return (
      <p role="status">
        Carregando suas preferências…
      </p>
    );
  }

  if (loadError) {
    return (
      <Card className="trips-empty">
        <p role="alert">{loadError}</p>

        <Button
          onClick={() =>
            setRetry((value) => value + 1)
          }
        >
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!form) {
    return null;
  }

  function control(name, label, options = {}) {
    const {
      choices,
      hint,
      ...props
    } = options;

    const attributes = {
      id: name,
      name,
      value: form[name],
      onChange: change,

      "aria-invalid": Boolean(errors[name]),

      "aria-describedby":
        [
          hint && `${name}-hint`,
          errors[name] && `${name}-error`,
        ]
          .filter(Boolean)
          .join(" ") || undefined,

      ...props,
    };

    return (
      <Field
        id={name}
        label={label}
        hint={hint}
        error={errors[name]}
      >
        {choices ? (
          <select {...attributes}>
            {choices.map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        ) : (
          <input {...attributes} />
        )}
      </Field>
    );
  }

  return (
    <>
      <PageHeading
        eyebrow="Nova viagem"
        title="A próxima viagem começa aqui."
        description="Conte o essencial. Você pode ajustar os detalhes depois."
      />

      <Card className="new-trip-card">
        <form
          ref={formRef}
          onSubmit={submit}
          noValidate
          aria-busy={pending}
        >
          {message && (
            <p
              ref={messageRef}
              tabIndex={-1}
              className="trips-error"
              role="alert"
            >
              {message}
            </p>
          )}

          <fieldset
            disabled={pending}
            className="new-trip-fields"
          >
            <legend className="sr-only">
              Planejamento da viagem
            </legend>

            <fieldset className="trip-modes">
              <legend>
                Como você vai planejar?
              </legend>

              <div>
                {[
                  ["solo", "Por conta própria"],
                  ["group", "Com amigos"],
                ].map(([value, label]) => (
                  <label
                    key={value}
                    className={
                      form.mode === value
                        ? "selected"
                        : ""
                    }
                  >
                    <input
                      type="radio"
                      name="mode"
                      value={value}
                      checked={form.mode === value}
                      onChange={change}
                    />

                    {label}
                  </label>
                ))}
              </div>

              {errors.mode && (
                <p
                  className="field-error"
                  role="alert"
                >
                  {errors.mode}
                </p>
              )}
            </fieldset>

            {control(
              "title",
              "Nome da viagem",
              {
                required: true,
                maxLength: 120,
                placeholder:
                  "Ex.: Lisboa com calma",
              },
            )}

            <div className="new-trip-row">
              {control(
                "origin",
                "Cidade de origem",
                {
                  required: true,
                  maxLength: 120,
                },
              )}

              <div className="trip-destination">
                {control(
                  "destination",
                  "Destino (opcional)",
                  {
                    maxLength: 120,
                    disabled: form.undecided,
                  },
                )}

                <label className="trip-checkbox">
                  <input
                    type="checkbox"
                    name="undecided"
                    checked={form.undecided}
                    onChange={change}
                  />

                  Ainda não escolhi meu destino
                </label>
              </div>
            </div>

            <div className="new-trip-row">
              {control(
                "start_date",
                "Data de início",
                {
                  type: "date",
                  required: true,
                },
              )}

              {control(
                "end_date",
                "Data de término",
                {
                  type: "date",
                  required: true,

                  min:
                    form.start_date ||
                    undefined,

                  hint:
                    "Até 60 dias, incluindo o primeiro e o último.",
                },
              )}
            </div>

            <div className="new-trip-row">
              {control(
                "travelers_count",
                "Viajantes",
                {
                  type: "number",
                  required: true,
                  min: 1,
                  max: 50,
                  step: 1,
                },
              )}

              {control(
                "budget",
                "Orçamento total (R$)",
                {
                  inputMode: "decimal",
                  placeholder:
                    "Ex.: 32000,00",

                  hint:
                    "Opcional. Deixe vazio se ainda não definiu.",
                },
              )}
            </div>

            <h2>
              Como você gosta de viajar?
            </h2>

            <p className="muted">
              Preferências do perfil preenchidas.
              Você pode ajustá-las para esta viagem.
            </p>

            <div className="new-trip-preferences">
              {control("style", "Estilo", {
                choices: [
                  ["", "Não informado"],
                  ...travelStyles,
                ],
              })}

              {control("pace", "Ritmo", {
                choices: [
                  ["", "Não informado"],
                  ...travelPaces,
                ],
              })}

              {control(
                "transport",
                "Transporte",
                {
                  choices: [
                    ["", "Não informado"],
                    ...transports,
                  ],
                },
              )}
            </div>

            <fieldset className="trip-interests">
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
                        onChange={(event) => {
                          const checked =
                            event.target.checked;

                          setForm((current) => ({
                            ...current,

                            interests: checked
                              ? [
                                  ...current.interests,
                                  value,
                                ]
                              : current.interests.filter(
                                  (item) =>
                                    item !== value,
                                ),
                          }));

                          setErrors((current) => ({
                            ...current,
                            interests: "",
                          }));

                          setMessage("");
                        }}
                      />

                      {label}
                    </label>
                  ),
                )}
              </div>

              {errors.interests && (
                <p
                  className="field-error"
                  role="alert"
                >
                  {errors.interests}
                </p>
              )}
            </fieldset>

            <div className="new-trip-actions">
              <ButtonLink
                to="/viagens"
                variant="secondary"
              >
                Cancelar
              </ButtonLink>

              <Button type="submit">
                {pending
                  ? "Criando viagem…"
                  : "Criar viagem"}
              </Button>
            </div>
          </fieldset>

          {pending && (
            <p role="status" className="muted">
              Aguarde a confirmação do servidor.
            </p>
          )}
        </form>
      </Card>
    </>
  );
}