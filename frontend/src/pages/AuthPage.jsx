import { useEffect, useRef, useState } from "react";

import {
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";

import {
  Button,
  Card,
  Field,
  PageHeading,
} from "../components/ui";

import { useAuth } from "../contexts/AuthContext";

import "./auth.css";

export default function AuthPage({ mode }) {
  const signup = mode === "register";

  const {
    user,
    isRestoring,
    sessionError,
    login,
    register,
  } = useAuth();

  const navigate = useNavigate();

  const [values, setValues] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    password_confirm: "",
  });

  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const formRef = useRef(null);
  const messageRef = useRef(null);
  const requestRef = useRef(null);

  useEffect(() => {
    return () => requestRef.current?.abort();
  }, []);

  useEffect(() => {
    if (message) {
      messageRef.current?.focus();
    } else if (Object.keys(errors).length) {
      formRef.current
        ?.querySelector('[aria-invalid="true"]')
        ?.focus();
    }
  }, [message, errors]);

  if (isRestoring) {
    return (
      <p role="status">
        Verificando sua sessão…
      </p>
    );
  }

  if (user) {
    return <Navigate to="/viagens" replace />;
  }

  function change(event) {
    const { name, value } = event.target;

    setValues((current) => ({
      ...current,
      [name]: value,
    }));

    setErrors((current) => ({
      ...current,
      [name]: "",
    }));

    setMessage("");
  }

  async function submit(event) {
    event.preventDefault();

    if (requestRef.current || pending) {
      return;
    }

    const nextErrors = {};
    const email = values.email.trim();

    if (!email) {
      nextErrors.email = "Informe seu e-mail.";
    } else if (
      formRef.current.elements.email.validity.typeMismatch
    ) {
      nextErrors.email = "Informe um e-mail válido.";
    }

    if (!values.password) {
      nextErrors.password = "Informe sua senha.";
    }

    if (signup) {
      if (!values.first_name.trim()) {
        nextErrors.first_name = "Informe seu nome.";
      }

      if (
        values.password &&
        values.password.length < 8
      ) {
        nextErrors.password =
          "Use pelo menos 8 caracteres.";
      }

      if (!values.password_confirm) {
        nextErrors.password_confirm =
          "Confirme sua senha.";
      } else if (
        values.password !== values.password_confirm
      ) {
        nextErrors.password_confirm =
          "As senhas não coincidem.";
      }
    }

    setErrors(nextErrors);
    setMessage("");

    if (Object.keys(nextErrors).length) {
      return;
    }

    const controller = new AbortController();

    requestRef.current = controller;
    setPending(true);

    try {
      const data = signup
        ? {
            ...values,
            first_name: values.first_name.trim(),
            last_name: values.last_name.trim(),
            email,
          }
        : {
            email,
            password: values.password,
          };

      await (signup ? register : login)(
        data,
        controller.signal,
      );

      if (!controller.signal.aborted) {
        navigate("/viagens", { replace: true });
      }
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      const fieldErrors = {};

      for (const name of Object.keys(values)) {
        if (error.fields?.[name]) {
          fieldErrors[name] = error.fields[name];
        }
      }

      setErrors(fieldErrors);

      if (
        !Object.keys(fieldErrors).length ||
        error.fields?.detail ||
        error.fields?.non_field_errors
      ) {
        setMessage(
          error.message ||
            "Não foi possível concluir o acesso. Tente novamente.",
        );
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
      }

      if (!controller.signal.aborted) {
        setPending(false);
      }
    }
  }

  function input(
    name,
    label,
    {
      type = "text",
      autoComplete,
      hint,
      maxLength,
      required = true,
    } = {},
  ) {
    const describedBy = [
      hint && `${name}-hint`,
      errors[name] && `${name}-error`,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <Field
        id={name}
        label={label}
        error={errors[name]}
        hint={hint}
      >
        <input
          id={name}
          name={name}
          type={type}
          autoComplete={autoComplete}
          maxLength={maxLength}
          required={required}
          value={values[name]}
          onChange={change}
          aria-invalid={Boolean(errors[name])}
          aria-describedby={describedBy || undefined}
        />
      </Field>
    );
  }

  return (
    <div className="auth-page">
      <PageHeading
        eyebrow={
          signup
            ? "Crie sua conta"
            : "Bem-vinda de volta"
        }
        title={
          signup
            ? "Encontre o seu rumo."
            : "Seu próximo capítulo espera."
        }
        description={
          signup
            ? "Comece pelos seus dados de acesso."
            : "Entre para continuar seus planos."
        }
      />

      <Card>
        <form
          ref={formRef}
          noValidate
          onSubmit={submit}
          aria-busy={pending}
        >
          {sessionError && !message && (
            <p className="auth-error" role="status">
              {sessionError}
            </p>
          )}

          {message && (
            <p
              ref={messageRef}
              className="auth-error"
              role="alert"
              tabIndex={-1}
            >
              {message}
            </p>
          )}

          <fieldset
            disabled={pending}
            className="auth-fields"
          >
            <legend className="sr-only">
              {signup
                ? "Dados de cadastro"
                : "Dados de acesso"}
            </legend>

            {signup && (
              <div className="auth-name-row">
                {input("first_name", "Nome", {
                  autoComplete: "given-name",
                  maxLength: 150,
                })}

                {input(
                  "last_name",
                  "Sobrenome (opcional)",
                  {
                    autoComplete: "family-name",
                    maxLength: 150,
                    required: false,
                  },
                )}
              </div>
            )}

            {input("email", "E-mail", {
              type: "email",
              autoComplete: "email",
              maxLength: 254,
            })}

            {input("password", "Senha", {
              type: showPassword ? "text" : "password",

              autoComplete: signup
                ? "new-password"
                : "current-password",

              hint: signup
                ? "Use pelo menos 8 caracteres. Evite senhas comuns, apenas números ou semelhantes aos seus dados."
                : undefined,
            })}

            {signup &&
              input(
                "password_confirm",
                "Confirmar senha",
                {
                  type: showPassword
                    ? "text"
                    : "password",

                  autoComplete: "new-password",
                },
              )}

            <label className="auth-show-password">
              <input
                type="checkbox"
                checked={showPassword}
                onChange={(event) =>
                  setShowPassword(event.target.checked)
                }
              />

              Mostrar {signup ? "senhas" : "senha"}
            </label>

            <Button
              type="submit"
              className="auth-submit"
            >
              {pending
                ? signup
                  ? "Criando conta…"
                  : "Entrando…"
                : signup
                  ? "Criar conta"
                  : "Entrar"}
            </Button>
          </fieldset>

          {pending && (
            <p className="muted" role="status">
              Aguarde a confirmação do servidor.
            </p>
          )}
        </form>

        <p className="auth-switch">
          {signup
            ? "Já tem uma conta? "
            : "Ainda não tem uma conta? "}

          <Link to={signup ? "/entrar" : "/cadastro"}>
            {signup ? "Entrar" : "Criar conta"}
          </Link>
        </p>
      </Card>
    </div>
  );
}