import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Badge,
  Button,
  Card,
  Field,
} from "../ui";

import Feedback from "../Feedback";
import DestinationResults from "./DestinationResults";

import {
  generateGroupDestinations,
  getGroupDestinations,
  getQuestionnaireProgress,
} from "../../services/groupDestinations";

import {
  personName,
} from "../../utils/questionnaire";

export default function DestinationPanel({
  tripId,
  isOwner,
  userId,
  dirty,
  onBusy,
  onFailure,
}) {
  const [progress, setProgress] = useState(null);

  const [
    destinations,
    setDestinations,
  ] = useState(null);

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [country, setCountry] = useState("BR");

  const [
    generating,
    setGenerating,
  ] = useState(false);

  const [
    generationError,
    setGenerationError,
  ] = useState("");

  const [
    countryError,
    setCountryError,
  ] = useState("");

  const actionRef = useRef(null);
  const initialized = useRef(false);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setErrors({});
    setProgress(null);
    setDestinations(null);

    Promise.allSettled([
      getQuestionnaireProgress(
        tripId,
        { signal: controller.signal },
      ),
      getGroupDestinations(
        tripId,
        { signal: controller.signal },
      ),
    ]).then(([group, result]) => {
      if (controller.signal.aborted) {
        return;
      }

      const failures = {};

      if (group.status === "fulfilled") {
        setProgress(group.value);
      } else {
        failures.progress = group.reason.message;
        onFailure(group.reason);
      }

      if (result.status === "fulfilled") {
        setDestinations(result.value);

        if (
          !initialized.current &&
          result.value.result
        ) {
          setCountry(
            result.value.result.origin_country_code,
          );
        }

        initialized.current = true;
      } else {
        failures.destinations =
          result.reason.message;

        onFailure(result.reason);
      }

      setErrors(failures);
      setLoading(false);
    });

    return () => controller.abort();
  }, [
    tripId,
    retry,
    onFailure,
  ]);

  useEffect(
    () => () => {
      actionRef.current?.abort();
      onBusy(false);
    },
    [onBusy],
  );

  async function generate() {
    if (
      actionRef.current ||
      loading ||
      dirty ||
      !progress?.all_answered ||
      !isOwner ||
      !destinations
    ) {
      return;
    }

    if (!/^[A-Z]{2}$/.test(country)) {
      setCountryError(
        "Informe duas letras, por exemplo BR para Brasil.",
      );

      return;
    }

    const controller = new AbortController();

    actionRef.current = controller;

    setGenerating(true);
    onBusy(true);
    setGenerationError("");
    setCountryError("");

    try {
      const result = await generateGroupDestinations(
        tripId,
        {
          origin_country_code: country,
          refresh: Boolean(
            destinations.available,
          ),
        },
        { signal: controller.signal },
      );

      if (!controller.signal.aborted) {
        setDestinations(result);
      }
    } catch (failure) {
      if (controller.signal.aborted) {
        return;
      }

      setGenerationError(failure.message);
      onFailure(failure);

      if (
        [400, 409].includes(failure.status)
      ) {
        setRetry((value) => value + 1);
      }
    } finally {
      if (!controller.signal.aborted) {
        actionRef.current = null;
        setGenerating(false);
        onBusy(false);
      }
    }
  }

  const canGenerate =
    !loading &&
    !generating &&
    !dirty &&
    progress?.all_answered &&
    Boolean(destinations);

  return (
    <div className="destination-panel">
      <Card>
        <h2>Respostas do grupo</h2>

        <Button
          variant="secondary"
          disabled={loading || generating}
          onClick={() =>
            setRetry((value) => value + 1)
          }
        >
          Atualizar progresso e resultados
        </Button>

        <p className="muted">
          Atualizar consulta somente os dados salvos,
          sem chamar a IA.
        </p>

        {loading && (
          <Feedback
            kind="loading"
            title="Consultando respostas e resultados…"
          />
        )}

        {errors.progress && (
          <Feedback
            kind="error"
            title="Não foi possível carregar o progresso."
            detail={errors.progress}
            onRetry={() =>
              setRetry((value) => value + 1)
            }
          />
        )}

        {progress && (
          <>
            <p>
              {progress.answered_count} de{" "}
              {progress.total_members}{" "}
              integrante(s) responderam.
            </p>

            <progress
              className="destination-progress"
              value={progress.answered_count}
              max={progress.total_members || 1}
              aria-label="Progresso dos questionários"
            />

            <ul className="destination-members">
              {progress.members.map(
                (member) => (
                  <li key={member.user.id}>
                    <span>
                      {personName(member.user)}

                      {member.user.id === userId
                        ? " (você)"
                        : ""}
                    </span>

                    <Badge>
                      {member.answered
                        ? "Respondido"
                        : "Pendente"}
                    </Badge>
                  </li>
                ),
              )}
            </ul>

            {!progress.all_answered && (
              <p>
                A geração será liberada quando a
                organizadora e todos os integrantes
                aceitos responderem. Convites pendentes
                não entram na contagem.
              </p>
            )}
          </>
        )}
      </Card>

      <Card>
        <h2>Encontrar o destino ideal</h2>

        {isOwner ? (
          <>
            <Field
              id="origin-country"
              label="País de origem — código de duas letras"
              hint="BR para Brasil, PT para Portugal, ES para Espanha. Confirme o país da cidade de partida."
              error={countryError}
            >
              <input
                id="origin-country"
                value={country}
                maxLength="2"
                disabled={generating}
                onChange={(event) => {
                  setCountry(
                    event.target.value.toUpperCase(),
                  );

                  setCountryError("");
                }}
                aria-invalid={Boolean(countryError)}
                aria-describedby={
                  countryError
                    ? "origin-country-error"
                    : "origin-country-hint"
                }
              />
            </Field>

            <p className="muted">
              Este botão consulta o Gemini e usa
              sua cota da API.
            </p>

            {dirty && (
              <p role="status">
                Salve as alterações do seu questionário
                antes de gerar recomendações.
              </p>
            )}

            <Button
              disabled={!canGenerate}
              onClick={generate}
            >
              {generating
                ? "Analisando preferências…"
                : destinations?.available
                  ? "Gerar novas recomendações"
                  : "Gerar recomendações"}
            </Button>
          </>
        ) : (
          <p>
            A organizadora gera as recomendações após
            todos responderem. Você pode consultar os
            resultados salvos e atualizar o progresso.
          </p>
        )}

        {generating && (
          <Feedback
            kind="loading"
            title="Analisando as preferências do grupo…"
            detail="Aguarde a resposta do assistente. O tempo depende da disponibilidade do serviço."
          />
        )}

        {generationError && (
          <Feedback
            kind="error"
            title="Não foi possível gerar recomendações."
            detail={generationError}
            onRetry={
              isOwner
                ? generate
                : undefined
            }
            busy={!canGenerate}
          />
        )}

        {errors.destinations && (
          <Feedback
            kind="error"
            title="Não foi possível consultar as recomendações."
            detail={errors.destinations}
            onRetry={() =>
              setRetry((value) => value + 1)
            }
          />
        )}

        {destinations?.stale && (
          <Feedback
            kind="info"
            title="As recomendações precisam ser atualizadas."
            detail="As respostas, os integrantes ou os dados da viagem mudaram desde a última geração."
          />
        )}

        {destinations &&
          !destinations.available &&
          !destinations.stale && (
            <Feedback
              kind="empty"
              title="O grupo ainda não tem recomendações."
              detail="Após o preenchimento dos questionários, a organizadora poderá solicitar os destinos."
            />
          )}
      </Card>

      {destinations?.available &&
        destinations.result && (
          <DestinationResults
            data={destinations}
            currentUserId={userId}
          />
        )}
    </div>
  );
}