import { useEffect, useRef, useState } from "react";

import {
  Link,
  NavLink,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { Avatar } from "./ui";
import { useAuth } from "../contexts/AuthContext";

const navigation = [
  { to: "/viagens", label: "Minhas viagens" },
  { to: "/lugares", label: "Meus lugares" },
  { to: "/amigos", label: "Amigos" },
];

export default function Header() {
  const { user, isRestoring, logout } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const [accountOpen, setAccountOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  const accountRef = useRef(null);
  const triggerRef = useRef(null);

  const name = user?.first_name || "Conta";

  const initials = user
    ? (
        `${user.first_name?.[0] || ""}` +
        `${user.last_name?.[0] || ""}`
      ).toUpperCase() || "EU"
    : "EU";

  async function handleLogout() {
    if (loggingOut) {
      return;
    }

    setLoggingOut(true);
    setLogoutError("");

    try {
      await logout();

      setAccountOpen(false);
      navigate("/entrar", { replace: true });
    } catch (error) {
      setLogoutError(error.message);
    } finally {
      setLoggingOut(false);
    }
  }

  useEffect(() => {
    setAccountOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function closeOutside(event) {
      if (!accountRef.current?.contains(event.target)) {
        setAccountOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape" && accountOpen) {
        setAccountOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("focusin", closeOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener(
        "pointerdown",
        closeOutside,
      );

      document.removeEventListener(
        "focusin",
        closeOutside,
      );

      document.removeEventListener(
        "keydown",
        handleEscape,
      );
    };
  }, [accountOpen]);

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link
          to="/viagens"
          className="brand"
          aria-label="Rumo — início"
        >
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <circle
              cx="16"
              cy="16"
              r="16"
              fill="currentColor"
            />

            <path
              d="m9 22 7-15 7 15-7-6Z"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>

          rumo
        </Link>

        <nav
          className="primary-nav"
          aria-label="Navegação principal"
        >
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "is-active" : ""
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="header-actions">
          <NavLink to="/ajuda" className="help-link">
            Ajuda
          </NavLink>

          <div className="account" ref={accountRef}>
            <button
              type="button"
              className="account-trigger"
              ref={triggerRef}
              aria-expanded={accountOpen}
              aria-controls={
                accountOpen
                  ? "account-navigation"
                  : undefined
              }
              onClick={() =>
                setAccountOpen((current) => !current)
              }
            >
              <span aria-hidden="true">
                <Avatar name={name} initials={initials} />
              </span>

              <span>
                {isRestoring ? "Aguarde…" : name}
              </span>

              <span aria-hidden="true">⌄</span>
            </button>

            {accountOpen && (
              <nav
                id="account-navigation"
                className="account-panel"
                aria-label="Menu da conta"
              >
                <p className="eyebrow">Sua conta</p>

                <Link to="/conta">
                  Perfil e preferências
                </Link>

                <Link to="/conta/seguranca">
                  Segurança
                </Link>

                <Link to="/conta/historico">
                  Histórico de viagens
                </Link>

                <div className="menu-divider" />

                {user ? (
                  <>
                    <button
                      type="button"
                      disabled={loggingOut}
                      onClick={handleLogout}
                    >
                      {loggingOut ? "Saindo…" : "Sair"}
                    </button>

                    {logoutError && (
                      <p
                        className="logout-error"
                        role="alert"
                      >
                        {logoutError}
                      </p>
                    )}
                  </>
                ) : !isRestoring && (
                  <>
                    <Link to="/entrar">Entrar</Link>

                    <Link to="/cadastro">
                      Criar conta
                    </Link>
                  </>
                )}
              </nav>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}