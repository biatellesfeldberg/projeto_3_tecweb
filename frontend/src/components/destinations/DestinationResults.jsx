import {
  Badge,
  Card,
} from "../ui";

import {
  compatibilityLabels,
  formatScore,
  personName,
} from "../../utils/questionnaire";

const money = (value, currency) =>
  new Intl.NumberFormat(
    "pt-BR",
    {
      style: "currency",
      currency,
    },
  ).format(Number(value));

function DestinationCard({
  destination,
  currency,
  main,
  currentUserId,
}) {
  const {
    compatibility,
    estimated_cost_per_person: personCost,
    estimated_group_cost: groupCost,
  } = destination;

  return (
    <Card
      className={
        main
          ? "destination-main"
          : ""
      }
    >
      <p className="eyebrow">
        {main
          ? "Recomendação principal"
          : "Alternativa"}
      </p>

      <h3>
        {destination.city}, {destination.country}
      </h3>

      <Badge>
        Compatibilidade{" "}
        {compatibilityLabels[
          compatibility.label
        ]?.toLowerCase()}
        {" · "}
        {formatScore(compatibility.score)}/100
      </Badge>

      <p>{destination.reason}</p>

      <dl className="destination-costs">
        <div>
          <dt>Duração nas datas da viagem</dt>

          <dd>
            {destination.duration_days} dia(s)
          </dd>
        </div>

        <div>
          <dt>Estimativa por pessoa</dt>

          <dd>
            {money(personCost.min, currency)}
            {" a "}
            {money(personCost.max, currency)}
          </dd>
        </div>

        <div>
          <dt>Estimativa para o grupo</dt>

          <dd>
            {money(groupCost.min, currency)}
            {" a "}
            {money(groupCost.max, currency)}
          </dd>
        </div>
      </dl>

      <h4>Compatibilidade por integrante</h4>

      {compatibility.members?.length ? (
        <div className="destination-table-scroll">
          <table className="destination-table">
            <caption className="sr-only">
              Compatibilidade individual com{" "}
              {destination.city}
            </caption>

            <thead>
              <tr>
                <th scope="col">Integrante</th>
                <th scope="col">Nota</th>
                <th scope="col">
                  Compatibilidade
                </th>
              </tr>
            </thead>

            <tbody>
              {compatibility.members.map(
                (item) => (
                  <tr key={item.user.id}>
                    <th scope="row">
                      {personName(item.user)}

                      {item.user.id === currentUserId
                        ? " (você)"
                        : ""}
                    </th>

                    <td>
                      {formatScore(item.score)}/100
                    </td>

                    <td>
                      {compatibilityLabels[item.label]}

                      <meter
                        min="0"
                        max="100"
                        value={item.score}
                        aria-label={
                          `Compatibilidade de ${
                            personName(item.user)
                          } com ${destination.city}`
                        }
                      />
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <p>
          Atualize o backend para consultar
          as notas individuais.
        </p>
      )}

      <h4>Conflitos de preferências</h4>

      {destination.conflicts.length ? (
        <ul>
          {destination.conflicts.map(
            (conflict) => (
              <li key={conflict.criterion}>
                {conflict.message}
              </li>
            ),
          )}
        </ul>
      ) : (
        <p>
          Nenhum conflito identificado
          nos critérios calculados.
        </p>
      )}

      <p className="muted">
        {destination.caveat}
      </p>
    </Card>
  );
}

export default function DestinationResults({
  data,
  currentUserId,
}) {
  const result = data.result;

  return (
    <section
      className="destination-results"
      aria-label="Destinos recomendados"
    >
      <h2>Destinos para o grupo</h2>

      <p className="muted">
        Gerado em{" "}
        {new Date(
          data.generated_at,
        ).toLocaleString("pt-BR")}
        {" · "}
        {result.participants_count} integrante(s).
      </p>

      <p>{result.cost_notice}</p>

      <DestinationCard
        destination={result.recommendation}
        currency={result.currency}
        main
        currentUserId={currentUserId}
      />

      <h3>Outras possibilidades</h3>

      <div className="destination-alternatives">
        {result.alternatives.map(
          (destination) => (
            <DestinationCard
              key={
                `${destination.country_code}-${destination.city}`
              }
              destination={destination}
              currency={result.currency}
              currentUserId={currentUserId}
            />
          ),
        )}
      </div>

      <details className="card destination-method">
        <summary>
          Como calculamos a compatibilidade?
        </summary>

        <p>
          A nota de cada pessoa considera orçamento
          (30 pontos), duração (15), interesses (20),
          paisagem (10), clima (10), ritmo (5), destino
          nacional/internacional (5) e hospedagem (5).
        </p>

        <p>
          Orçamento: limite individual dividido pelo
          custo máximo estimado, até 100%. Duração:
          menor número de dias dividido pelo maior.
          Interesses: proporção contemplada, com peso
          da gastronomia conforme a importância
          informada. Nas outras preferências, a
          pontuação é integral quando atendidas ou
          quando você escolhe “sem preferência”.
        </p>

        <p>
          A nota do grupo combina 70% da média com
          30% da menor nota individual. Alta: 80 a
          100; média: 60 a menos de 80; baixa:
          abaixo de 60.
        </p>

        <p>
          {result.compatibility_method.notice}
        </p>
      </details>
    </section>
  );
}