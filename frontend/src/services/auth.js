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
    // A sessão atual continua em memória.
  }
}

export class AuthError extends Error {
  constructor(message, fields = {}, status = 0) {
    super(message);
    this.fields = fields;
    this.status = status;
  }
}

function formatMessages(value) {
  if (value && typeof value === "object") {
    return Object.values(value)
      .map(formatMessages)
      .join(" ");
  }

  return String(value);
}

export async function authRequest(
  path,
  {
    method = "GET",
    data,
    token,
    signal,
    responseType = "json",
  } = {},
) {
  const multipart = data instanceof FormData;

  let response;

  try {
    response = await fetch(`/api/auth/${path}/`, {
      method,
      signal,

      headers: {
        Accept:
          responseType === "blob"
            ? "*/*"
            : "application/json",

        ...(data && !multipart
          ? { "Content-Type": "application/json" }
          : {}),

        ...(token
          ? { Authorization: `Token ${token}` }
          : {}),
      },

      ...(data
        ? {
            body: multipart
              ? data
              : JSON.stringify(data),
          }
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

  if (response.ok && responseType === "blob") {
    const contentType =
      response.headers.get("Content-Type");

    if (!contentType?.startsWith("image/")) {
      throw new AuthError(
        "Não foi possível carregar a foto.",
      );
    }

    return response.blob();
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const fields = {};

    if (body && typeof body === "object") {
      for (const [key, value] of Object.entries(body)) {
        fields[key] = formatMessages(value);
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