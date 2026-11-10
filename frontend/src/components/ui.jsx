import { Link, NavLink } from "react-router-dom";

export function Button({
  children,
  variant = "primary",
  type = "button",
  className = "",
  ...props
}) {
  return (
    <button
      type={type}
      className={`button button--${variant} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function ButtonLink({
  children,
  variant = "primary",
  className = "",
  ...props
}) {
  return (
    <Link
      className={`button button--${variant} ${className}`}
      {...props}
    >
      {children}
    </Link>
  );
}

export function Card({ children, className = "", ...props }) {
  return (
    <section className={`card ${className}`} {...props}>
      {children}
    </section>
  );
}

export function Badge({ children }) {
  return <span className="badge">{children}</span>;
}

export function Avatar({
  name = "Conta",
  initials = "EU",
}) {
  return (
    <span className="avatar" role="img" aria-label={name}>
      {initials}
    </span>
  );
}

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}

        <h1>{title}</h1>

        {description && (
          <p className="muted heading-description">
            {description}
          </p>
        )}
      </div>

      {action && (
        <div className="heading-action">{action}</div>
      )}
    </div>
  );
}

export function Tabs({ items, label }) {
  return (
    <nav className="tabs" aria-label={label}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end
          className={({ isActive }) =>
            `tab ${isActive ? "is-active" : ""}`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

/*
  Exemplo de uso futuro:

  <Field id="nome" label="Nome">
    <input id="nome" name="nome" />
  </Field>

  Quando houver erro, passe aria-invalid e aria-describedby
  no input para associá-lo à mensagem.
*/
export function Field({
  id,
  label,
  hint,
  error,
  children,
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>

      {children}

      {hint && (
        <p id={`${id}-hint`} className="muted">
          {hint}
        </p>
      )}

      {error && (
        <p
          id={`${id}-error`}
          className="field-error"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}