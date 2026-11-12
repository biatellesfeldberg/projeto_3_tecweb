import {
  useEffect,
  useRef,
  useState,
} from "react";

import { useAuth } from "../contexts/AuthContext";

import {
  generateItinerary,
} from "../services/trips";

import { Button } from "./ui";
import Feedback from "./Feedback";

function generationMessage(error) {
  if (
    error.status === 404 ||
    error.status === 405
  ) {
    return (
      "Não foi possível acessar a geração deste roteiro. " +
      "Tente novamente mais tarde."
    );
  }

  if (error.status === 429) {
    return (
      error.message ||
      "O limite de solicitações foi atingido. Aguarde antes de tentar novamente."
    );
  }

  return (
    error.message ||
    "Não foi possível gerar o roteiro agora. Tente novamente."
  );
}

export default function ItineraryGeneration({
  trip,
}) {
  const { expireSession } = useAuth();

  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState("");

  const locked = useRef(false);
  const active = useRef(false);

  useEffect(() => {
    active.current = true;

    return () => {
      active.current = false;
    };
  }, []);

  async function generate() {
    if (
      locked.current ||
      !trip.destination
    ) {
      return;
    }

    locked.current = true;

    setPhase("loading");
    setError("");

    try {
      const result = await generateItinerary(
        trip.id,
        {
          replaceExisting: false,
        },
      );

      if (!active.current) {
        return;
      }

      if (
        Number(result?.id) !== Number(trip.id) ||
        !Array.isArray(result?.days)
      ) {
        throw new Error(
          "Não foi possível confirmar a geração. Tente novamente.",
        );
      }

      const hasActivities = result.days.some(
        (day) =>
          Array.isArray(day.activities) &&
          day.activities.length > 0,
      );

      setPhase(
        hasActivities
          ? "success"
          : "empty",
      );
    } catch (failure) {
      if (!active.current) {
        return;
      }

      if (failure.status === 401) {
        expireSession();
        return;
      }

      setError(generationMessage(failure));
      setPhase("error");
    } finally {
      locked.current = false;
    }
  }

  if (!trip.destination) {
    return (
      <Feedback
        kind="info"
        title="O destino ainda está em aberto."
        detail="A geração ficará disponível depois que a viagem tiver um destino."
      />
    );
  }

  const busy = phase === "loading";

  return (
    <div className="itinerary-feedback">
      <Button
        onClick={generate}
        disabled={
          busy ||
          phase === "success"
        }
        aria-busy={busy}
        variant="secondary"
      >
        {busy
          ? "Montando seu roteiro…"
          : phase === "success"
            ? "Roteiro atualizado"
            : phase === "error" ||
                phase === "empty"
              ? "Tentar novamente"
              : "Gerar roteiro"}
      </Button>

      {busy && (
        <Feedback
          kind="loading"
          title="Montando seu roteiro…"
          detail="Isso pode levar alguns instantes. Aguarde a confirmação antes de enviar novamente."
        />
      )}

      {phase === "error" && (
        <Feedback
          kind="error"
          title="Não foi possível gerar o roteiro."
          detail={error}
        />
      )}

      {phase === "empty" && (
        <Feedback
          kind="empty"
          title="Nenhuma atividade foi retornada."
          detail="Você pode tentar novamente. As atividades existentes não serão substituídas."
        />
      )}

      {phase === "success" && (
        <Feedback
          kind="success"
          title="Roteiro atualizado com sucesso."
          detail="As atividades retornadas foram salvas para esta viagem."
        />
      )}
    </div>
  );
}