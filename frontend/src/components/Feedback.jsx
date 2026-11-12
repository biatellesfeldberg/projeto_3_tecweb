import { Button } from "./ui";
import "./feedback.css";

export default function Feedback({
  kind = "info",
  title,
  detail,
  onRetry,
  retryLabel = "Tentar novamente",
  busy = false,
  children,
}) {
  const loading = kind === "loading";

  return (
    <div
      className={`feedback feedback--${kind}`}
      role={kind === "error" ? "alert" : "status"}
      aria-atomic="true"
    >
      <span
        className={
          loading
            ? "feedback-spinner"
            : "feedback-symbol"
        }
        aria-hidden="true"
      >
        {loading
          ? ""
          : kind === "error"
            ? "!"
            : kind === "success"
              ? "✓"
              : "↗"}
      </span>

      <div className="feedback-content">
        <p className="feedback-title">
          {title}
        </p>

        {detail && (
          <p className="feedback-detail">
            {detail}
          </p>
        )}

        {(onRetry || children) && (
          <div className="feedback-actions">
            {onRetry && (
              <Button
                onClick={onRetry}
                disabled={loading || busy}
              >
                {retryLabel}
              </Button>
            )}

            {children}
          </div>
        )}
      </div>
    </div>
  );
}