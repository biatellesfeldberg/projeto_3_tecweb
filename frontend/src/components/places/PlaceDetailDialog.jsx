import { useState } from "react";

import Modal from "../Modal";
import { Badge, Button } from "../ui";
import { PlaceCover } from "./PlaceCard";

import { categoryLabel, mapLink } from "../../utils/places";

/*
  Detalhes de um lugar, com ações de editar, excluir e tirar de uma viagem.
  As ações devolvem Promises; erros aparecem dentro da janela.
*/
export default function PlaceDetailDialog({
  place,
  onClose,
  onEdit,
  onDelete,
  onRemoveFromTrip,
}) {
  return (
    <Modal
      open={Boolean(place)}
      onClose={onClose}
      title={place?.name || ""}
      description={
        place
          ? [place.city, place.country].filter(Boolean).join(", ")
          : undefined
      }
    >
      {place && (
        <PlaceDetail
          key={place.id}
          place={place}
          onEdit={onEdit}
          onDelete={onDelete}
          onRemoveFromTrip={onRemoveFromTrip}
        />
      )}
    </Modal>
  );
}

function PlaceDetail({ place, onEdit, onDelete, onRemoveFromTrip }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const link = mapLink(place);

  async function run(action, key) {
    setBusy(key);
    setError("");

    try {
      await action();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="place-detail">
      {place.image_url && (
        <PlaceCover place={place} className="place-detail-cover" />
      )}

      <div className="place-detail-meta">
        <Badge>{categoryLabel(place.category)}</Badge>

        {link && (
          <a href={link} target="_blank" rel="noreferrer">
            Ver no mapa ↗
          </a>
        )}
      </div>

      {error && (
        <p className="place-form-error" role="alert">
          {error}
        </p>
      )}

      {place.description && (
        <section>
          <h3>Descrição</h3>
          <p className="place-text">{place.description}</p>
        </section>
      )}

      <section>
        <h3>Observações</h3>
        <p className={`place-text ${place.notes ? "" : "muted"}`}>
          {place.notes || "Nenhuma observação ainda."}
        </p>
      </section>

      {place.address && (
        <section>
          <h3>Endereço</h3>
          <p className="place-text">{place.address}</p>
        </section>
      )}

      <section>
        <h3>Viagens</h3>

        {place.trips.length === 0 ? (
          <p className="muted">
            Ainda sem viagem. Selecione o lugar na sua coleção e use
            “Adicionar à viagem”.
          </p>
        ) : (
          <ul className="place-detail-trips">
            {place.trips.map((trip) => (
              <li key={trip.id}>
                <span>{trip.title}</span>

                <Button
                  variant="ghost"
                  disabled={Boolean(busy)}
                  onClick={() =>
                    run(
                      () => onRemoveFromTrip(place, trip),
                      `trip-${trip.id}`,
                    )
                  }
                >
                  {busy === `trip-${trip.id}`
                    ? "Removendo…"
                    : "Tirar desta viagem"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {confirming ? (
        <div className="place-confirm" role="alert">
          <p>
            <strong>Excluir “{place.name}”?</strong> Ele sai da sua coleção e
            de todas as viagens. O roteiro não é alterado.
          </p>

          <div className="modal-actions">
            <Button
              variant="secondary"
              onClick={() => setConfirming(false)}
              disabled={Boolean(busy)}
            >
              Cancelar
            </Button>

            <Button
              className="button--danger"
              onClick={() => run(() => onDelete(place), "delete")}
              disabled={Boolean(busy)}
            >
              {busy === "delete" ? "Excluindo…" : "Sim, excluir"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="modal-actions">
          <Button
            variant="ghost"
            className="place-delete"
            onClick={() => setConfirming(true)}
            disabled={Boolean(busy)}
          >
            Excluir
          </Button>

          <Button onClick={() => onEdit(place)} disabled={Boolean(busy)}>
            Editar
          </Button>
        </div>
      )}
    </div>
  );
}
