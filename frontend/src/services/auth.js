const TOKEN_KEY = "rumo.auth.token";

export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveToken(token) {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // A sessão atual continua em memória se o navegador
    // bloquear o armazenamento.
  }
}

export class AuthError extends Error {
  constructor(message, fields = {}, status = 0) {
    super(message);
    this.fields = fields;
    this.status = status;
  }
}

export async function authRequest(
  path,
  { method = "GET", data, token, signal } = {},
) {
  let response;

  try {
    response = await fetch(`/api/auth/${path}/`, {
      method,
      signal,

      headers: {
        Accept: "application/json",

        ...(data
          ? { "Content-Type": "application/json" }
          : {}),

        ...(token
          ? { Authorization: `Token ${token}` }
          : {}),
      },

      ...(data
        ? { body: JSON.stringify(data) }
        : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new AuthError(
      "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const fields = {};

    if (body && typeof body === "object") {
      for (const [key, value] of Object.entries(body)) {
        fields[key] = Array.isArray(value)
          ? value.join(" ")
          : String(value);
      }
    }

    throw new AuthError(
      response.status >= 500
        ? "O servidor está indisponível. Tente novamente em instantes."
        : fields.detail ||
            fields.non_field_errors ||
            "Confira os campos informados e tente novamente.",
      fields,
      response.status,
    );
  }

  if (!body || typeof body !== "object") {
    throw new AuthError(
      "O servidor retornou uma resposta inesperada. Tente novamente.",
    );
  }

  return body;
}