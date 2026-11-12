import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";

import {
  Avatar,
  Button,
  Card,
  Field,
  PageHeading,
} from "../components/ui";

import { useAuth } from "../contexts/AuthContext";

import "./profile.css";

const styles = [
  ["economic", "Econômico"],
  ["intermediate", "Intermediário"],
  ["comfort", "Conforto / luxuoso"],
];

const paces = [
  ["relaxed", "Tranquilo"],
  ["moderate", "Moderado"],
  ["intense", "Intenso"],
];

const ranges = [
  ["any", "Sem preferência"],
  ["domestic", "Nacionais"],
  ["international", "Internacionais"],
];

const interests = [
  ["beach", "Praia"],
  ["nature", "Natureza"],
  ["gastronomy", "Gastronomia"],
  ["adventure", "Aventura"],
  ["culture", "Cultura"],
  ["shopping", "Compras"],
  ["nightlife", "Vida noturna"],
  ["sightseeing", "Paisagens"],
];

function toForm(profile) {
  return {
    first_name: profile.first_name || "",
    last_name: profile.last_name || "",
    home_city: profile.home_city || "",
    bio: profile.bio || "",
    style: profile.style || "",
    pace: profile.pace || "",

    destination_preference:
      profile.destination_preference || "any",

    interests: profile.interests || [],

    preferred_destinations: (
      profile.preferred_destinations || []
    ).join("\n"),
  };
}

export default function ProfilePage() {
  const {
    user,
    isRestoring,
    accountRequest,
  } = useAuth();

  const userId = user?.id;

  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retry, setRetry] = useState(0);

  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");

  const [photoLoading, setPhotoLoading] =
    useState(false);

  const [photoPending, setPhotoPending] =
    useState(false);

  const [photoError, setPhotoError] = useState("");
  const [photoSuccess, setPhotoSuccess] = useState("");
  const [photoVersion, setPhotoVersion] = useState(0);

  const requests = useRef(new Set());
  const busyRef = useRef(false);
  const formRef = useRef(null);
  const fileRef = useRef(null);

  // Cancela envios pendentes ao sair da tela.
  useEffect(() => {
    return () => {
      requests.current.forEach((controller) => {
        controller.abort();
      });
    };
  }, []);

  // Carrega os dados já existentes.
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
      .then((data) => {
        setProfile(data);
        setForm(toForm(data));
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

  // Prévia local da nova foto.
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }

    const url = URL.createObjectURL(file);

    setPreview(url);

    return () => URL.revokeObjectURL(url);
  }, [file]);

  // A foto do backend exige autenticação.
  useEffect(() => {
    setPhotoUrl("");
    setPhotoLoading(false);

    if (!profile?.photo) {
      return;
    }

    const controller = new AbortController();
    let url;

    setPhotoLoading(true);

    accountRequest("me/photo", {
      signal: controller.signal,
      responseType: "blob",
    })
      .then((blob) => {
        if (controller.signal.aborted) {
          return;
        }

        url = URL.createObjectURL(blob);
        setPhotoUrl(url);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setPhotoError(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setPhotoLoading(false);
        }
      });

    return () => {
      controller.abort();

      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [
    profile?.photo,
    photoVersion,
    accountRequest,
  ]);

  useEffect(() => {
    formRef.current
      ?.querySelector('[aria-invalid="true"]')
      ?.focus();
  }, [errors]);

  async function request(path, options) {
    const controller = new AbortController();

    requests.current.add(controller);

    try {
      return await accountRequest(path, {
        ...options,
        signal: controller.signal,
      });
    } finally {
      requests.current.delete(controller);
    }
  }

  function change(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));

    setErrors((current) => ({
      ...current,
      [name]: "",
    }));

    setMessage("");
    setSuccess("");
  }

  function chooseFile(event) {
    const selected = event.target.files?.[0];

    setPhotoError("");
    setPhotoSuccess("");

    if (!selected) {
      return;
    }

    const validTypes = [
      "image/jpeg",
      "image/png",
      "image/webp",
    ];

    if (
      !validTypes.includes(selected.type) ||
      selected.size > 5 * 1024 * 1024
    ) {
      setFile(null);
      event.target.value = "";

      setPhotoError(
        "Escolha uma imagem JPEG, PNG ou WebP de até 5 MB.",
      );

      return;
    }

    setFile(selected);
  }

  async function savePhoto(remove = false) {
    if (
      busyRef.current ||
      (!remove && !file)
    ) {
      return;
    }

    busyRef.current = true;

    setPhotoPending(true);
    setPhotoError("");
    setPhotoSuccess("");

    try {
      const data = new FormData();

      if (!remove) {
        data.append("photo", file);
      }

      const result = await request("me/photo", {
        method: remove ? "DELETE" : "PATCH",
        ...(!remove ? { data } : {}),
      });

      // Atualiza a foto sem apagar edições do formulário.
      setProfile((current) => ({
        ...current,
        photo: result.photo,
      }));

      setFile(null);

      if (fileRef.current) {
        fileRef.current.value = "";
      }

      setPhotoVersion((value) => value + 1);

      setPhotoSuccess(
        remove
          ? "Foto removida."
          : "Foto salva com sucesso.",
      );
    } catch (error) {
      if (error.name !== "AbortError") {
        setPhotoError(
          error.fields?.photo || error.message,
        );
      }
    } finally {
      busyRef.current = false;
      setPhotoPending(false);
    }
  }

  async function submit(event) {
    event.preventDefault();

    if (busyRef.current) {
      return;
    }

    const destinations = form.preferred_destinations
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);

    const nextErrors = {};

    if (!form.first_name.trim()) {
      nextErrors.first_name = "Informe seu nome.";
    }

    if (
      destinations.length > 20 ||
      destinations.some((item) => item.length > 120)
    ) {
      nextErrors.preferred_destinations =
        "Informe até 20 destinos, com até 120 caracteres em cada linha.";
    }

    setErrors(nextErrors);
    setMessage("");
    setSuccess("");

    if (Object.keys(nextErrors).length) {
      return;
    }

    busyRef.current = true;
    setSaving(true);

    try {
      const result = await request("me", {
        method: "PATCH",

        data: {
          ...form,

          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          home_city: form.home_city.trim(),

          preferred_destinations: destinations,
        },
      });

      setProfile(result);
      setForm(toForm(result));

      setSuccess(
        "Perfil e preferências salvos com sucesso.",
      );
    } catch (error) {
      if (error.name !== "AbortError") {
        setErrors(error.fields || {});
        setMessage(error.message);
      }
    } finally {
      busyRef.current = false;
      setSaving(false);
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
        Carregando seu perfil…
      </p>
    );
  }

  if (loadError) {
    return (
      <Card>
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

  if (!form || !profile) {
    return null;
  }

  const disabled = saving || photoPending;

  const name =
    `${profile.first_name} ${profile.last_name}`.trim();

  const initials =
    (
      `${profile.first_name?.[0] || ""}` +
      `${profile.last_name?.[0] || ""}`
    ).toUpperCase() || "EU";

  function control(name, label, options = {}) {
    const {
      kind = "input",
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
        {kind === "textarea" ? (
          <textarea {...attributes} />
        ) : kind === "select" ? (
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
        eyebrow="Seu perfil"
        title="O seu jeito de viajar."
        description="Seu perfil preenche os próximos planos. Cada viagem pode ter preferências diferentes."
      />

      <div className="profile-layout">
        <Card className="profile-photo-card">
          <h2>Sua foto</h2>

          <div className="profile-avatar">
            {preview || photoUrl ? (
              <img
                src={preview || photoUrl}
                alt={`Foto de ${name}`}
              />
            ) : (
              <Avatar
                name={name}
                initials={initials}
              />
            )}
          </div>

          <p>{name}</p>

          {photoLoading && (
            <p role="status">Carregando foto…</p>
          )}

          <label
            htmlFor="profile-photo"
            className="muted"
          >
            Alterar foto
          </label>

          <input
            ref={fileRef}
            id="profile-photo"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            disabled={disabled}
            onChange={chooseFile}
            aria-describedby="photo-hint"
          />

          <p id="photo-hint" className="muted">
            JPEG, PNG ou WebP, até 5 MB.
            A foto é salva separadamente.
          </p>

          {file && (
            <Button
              onClick={() => savePhoto()}
              disabled={disabled}
            >
              Salvar foto
            </Button>
          )}

          {profile.photo && (
            <Button
              variant="secondary"
              onClick={() => savePhoto(true)}
              disabled={disabled}
            >
              Remover foto
            </Button>
          )}

          {photoPending && (
            <p role="status">Salvando foto…</p>
          )}

          {photoError && (
            <div>
              <p
                role="alert"
                className="field-error"
              >
                {photoError}
              </p>

              {profile.photo && !photoUrl && (
                <Button
                  variant="ghost"
                  disabled={disabled}
                  onClick={() => {
                    setPhotoError("");

                    setPhotoVersion(
                      (value) => value + 1,
                    );
                  }}
                >
                  Tentar carregar foto
                </Button>
              )}
            </div>
          )}

          {photoSuccess && (
            <p
              role="status"
              className="profile-success"
            >
              {photoSuccess}
            </p>
          )}
        </Card>

        <Card>
          <form
            ref={formRef}
            onSubmit={submit}
            noValidate
            aria-busy={saving}
          >
            {message && (
              <p
                className="profile-error"
                role="alert"
              >
                {message}
              </p>
            )}

            {success && (
              <p
                className="profile-success"
                role="status"
              >
                {success}
              </p>
            )}

            <fieldset
              className="profile-fields"
              disabled={disabled}
            >
              <legend>
                Informações pessoais
              </legend>

              <div className="profile-row">
                {control("first_name", "Nome", {
                  required: true,
                  maxLength: 150,
                  autoComplete: "given-name",
                })}

                {control(
                  "last_name",
                  "Sobrenome",
                  {
                    maxLength: 150,
                    autoComplete: "family-name",
                  },
                )}
              </div>

              <Field
                id="profile-email"
                label="E-mail"
                hint="O e-mail de acesso não pode ser alterado nesta tela."
              >
                <input
                  id="profile-email"
                  type="email"
                  value={profile.email}
                  readOnly
                  aria-describedby="profile-email-hint"
                />
              </Field>

              {control(
                "home_city",
                "Cidade de origem",
                {
                  maxLength: 120,
                  autoComplete: "address-level2",
                },
              )}

              {control("bio", "Sobre você", {
                kind: "textarea",
                maxLength: 500,
                rows: 3,
                hint: "Até 500 caracteres.",
              })}

              <h2>Preferências de viagem</h2>

              <fieldset
                className="profile-interests"
                aria-describedby={
                  errors.interests
                    ? "interests-error"
                    : undefined
                }
              >
                <legend>Interesses</legend>

                <div className="profile-interest-list">
                  {interests.map(([value, label]) => (
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

                          setSuccess("");
                          setMessage("");
                        }}
                      />

                      {label}
                    </label>
                  ))}
                </div>

                {errors.interests && (
                  <p
                    id="interests-error"
                    className="field-error"
                    role="alert"
                  >
                    {errors.interests}
                  </p>
                )}
              </fieldset>

              <div className="profile-row">
                {control("style", "Estilo", {
                  kind: "select",

                  choices: [
                    ["", "Não informado"],
                    ...styles,
                  ],
                })}

                {control("pace", "Ritmo", {
                  kind: "select",

                  choices: [
                    ["", "Não informado"],
                    ...paces,
                  ],
                })}
              </div>

              {control(
                "preferred_destinations",
                "Destinos preferidos",
                {
                  kind: "textarea",
                  rows: 4,
                  hint:
                    "Um destino por linha. Até 20 destinos, com 120 caracteres cada.",
                },
              )}

              {control(
                "destination_preference",
                "Alcance",
                {
                  kind: "select",
                  choices: ranges,
                },
              )}

              <Button type="submit">
                {saving
                  ? "Salvando…"
                  : "Salvar alterações"}
              </Button>
            </fieldset>
          </form>
        </Card>
      </div>
    </>
  );
}