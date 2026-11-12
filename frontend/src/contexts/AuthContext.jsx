import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AuthError,
  authRequest,
  getToken,
  saveToken,
} from "../services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const [isRestoring, setIsRestoring] = useState(
    () => Boolean(getToken()),
  );

  const [sessionError, setSessionError] = useState("");

  const tokenRef = useRef(null);
  const revision = useRef(0);

  useEffect(() => {
    const token = getToken();

    if (!token) {
      setIsRestoring(false);
      return;
    }

    tokenRef.current = token;

    const controller = new AbortController();
    const currentRevision = revision.current;

    authRequest("me", {
      token,
      signal: controller.signal,
    })
      .then((profile) => {
        if (
          !controller.signal.aborted &&
          revision.current === currentRevision
        ) {
          setUser(profile);
        }
      })
      .catch((error) => {
        if (
          controller.signal.aborted ||
          revision.current !== currentRevision
        ) {
          return;
        }

        if (error.status === 401) {
          tokenRef.current = null;
          saveToken(null);

          setSessionError(
            "Sua sessão não é mais válida. Entre novamente.",
          );
        } else {
          setSessionError(
            "Não foi possível verificar sua sessão. Tente entrar novamente.",
          );
        }
      })
      .finally(() => {
        if (
          !controller.signal.aborted &&
          revision.current === currentRevision
        ) {
          setIsRestoring(false);
        }
      });

    return () => controller.abort();
  }, []);

  const expireSession = useCallback(() => {
    revision.current += 1;
    tokenRef.current = null;

    saveToken(null);
    setUser(null);
    setIsRestoring(false);

    setSessionError(
      "Sua sessão não é mais válida. Entre novamente.",
    );
  }, []);

  const accountRequest = useCallback(
    async (path, options = {}) => {
      if (!tokenRef.current) {
        throw new AuthError(
          "Entre novamente para acessar seu perfil.",
          {},
          401,
        );
      }

      const currentRevision = revision.current;

      try {
        const result = await authRequest(path, {
          ...options,
          token: tokenRef.current,
        });

        if (
          options.signal?.aborted ||
          currentRevision !== revision.current
        ) {
          throw new DOMException(
            "Requisição cancelada.",
            "AbortError",
          );
        }

        if (
          options.responseType !== "blob" &&
          result.id
        ) {
          setUser(result);
        }

        return result;
      } catch (error) {
        if (
          error.status === 401 &&
          currentRevision === revision.current
        ) {
          revision.current += 1;
          tokenRef.current = null;

          saveToken(null);
          setUser(null);

          setSessionError(
            "Sua sessão não é mais válida. Entre novamente.",
          );
        }

        throw error;
      }
    },
    [],
  );

  async function authenticate(path, data, signal) {
    const result = await authRequest(path, {
      method: "POST",
      data,
      signal,
    });

    if (signal?.aborted) {
      return;
    }

    if (
      typeof result.token !== "string" ||
      !result.token ||
      !result.user?.id
    ) {
      throw new AuthError(
        "Não foi possível confirmar o acesso. Tente novamente.",
      );
    }

    revision.current += 1;
    tokenRef.current = result.token;

    saveToken(result.token);
    setUser(result.user);
    setSessionError("");
    setIsRestoring(false);
  }

  async function logout() {
    try {
      await authRequest("logout", {
        method: "POST",
        token: tokenRef.current,
      });
    } catch (error) {
      // Um token já inválido também encerra a sessão local.
      if (error.status !== 401) {
        throw error;
      }
    }

    revision.current += 1;
    tokenRef.current = null;

    saveToken(null);
    setUser(null);
    setSessionError("");
    setIsRestoring(false);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token: tokenRef.current,
        isRestoring,
        sessionError,
        accountRequest,
        expireSession,

        login: (data, signal) =>
          authenticate("login", data, signal),

        register: (data, signal) =>
          authenticate("register", data, signal),

        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth deve ser usado dentro de AuthProvider.",
    );
  }

  return context;
}