import { useEffect, useState } from "react";

import { Button, ButtonLink } from "../ui";
import Feedback from "../Feedback";
import Modal from "../Modal";
import TripMap from "../TripMap";
import { PlaceCover } from "../places/PlaceCard";

import { listPlaces } from "../../services/places";
import {
  categoryLabel,
  filterPlaces,
  hasCoordinates,
  pluralize,
} from "../../utils/places";

/*
  Aba "Lugares" da viagem: lugares salvos vinculados a ela.
  - onAdd(placeIds), onRemove(place): Promises.
  - onAddToItinerary(place): abre o formulário de atividade preenchido.
*/
export default function TripPlacesTab({
  trip,
  places,
  loading,
  error,
  onRetry,
  onAdd,
  onRemove,
  onAddToItinerary,
}) {
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState("");
  const [activeId, setActiveId] = useState(null);

  async function remove(place) {
    setBusy(place.id);
    setActionError("");
    try {
      await onRemove(place);
    } catch (failure) {
      setActionError(failure.message);
    } finally {
      setBusy(null);
    }
  }

  if (error) {
    return (
      <Feedback
        kind="error"
        title="Não foi possível carregar os lugares da viagem."
        detail={error}
        onRetry={onRetry}
      />
    );
  }

  if (loading) {
    return <Feedback kind="loading" title="Carregando lugares…" />;
  }

  const located = places.filter(hasCoordinates);
  const points = located.map((place, index) => ({
    id: place.id,
    lat: Number(place.latitude),
    lng: Number(place.longitude),
    label: index + 1,
    title: place.name,
    detail: [place.city, categoryLabel(place.category)]
      .filter(Boolean)
      .join(" · "),
  }));
  const numbers = new Map(points.map((point) => [point.id, point.label]));

  const addButton = (
    <Button onClick={() => setAdding(true)}>
      + Trazer da minha coleção
    </Button>
  );

  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Lugares para esta viagem</h2>
          <p className="muted">
            Sugestões guardadas em Meus lugares. Elas também orientam a IA ao
            gerar o roteiro.
          </p>
        </div>
        {places.length > 0 && addButton}
      </div>

      {actionError && (
        <p className="place-form-error" role="alert">
          {actionError}
        </p>
      )}

      {places.length === 0 ? (
        <Feedback
          kind="empty"
          title="Nenhum lugar vinculado a esta viagem."
          detail="Traga lugares da sua coleção ou cadastre novos em Meus lugares."
        >
          {addButton}
          <ButtonLink to="/lugares" variant="secondary">
            Ir para Meus lugares
          </ButtonLink>
        </Feedback>
      ) : (
        <div className="itinerary-layout">
          <ul className="trip-places-list">
            {places.map((place) => (
              <li
                key={place.id}
                className={`trip-place ${
                  activeId === place.id ? "is-active" : ""
                }`}
              >
                <PlaceCover place={place} className="trip-place-cover" />

                <div className="trip-place-body">
                  <h3>{place.name}</h3>
                  <p className="muted">
                    {[place.city, categoryLabel(place.category)]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {place.notes && (
                    <p className="timeline-notes">{place.notes}</p>
                  )}

                  <div className="timeline-actions">
                    <button
                      type="button"
                      onClick={() => onAddToItinerary(place)}
                    >
                      Levar para o roteiro
                    </button>
                    {numbers.has(place.id) && (
                      <button
                        type="button"
                        onClick={() => setActiveId(place.id)}
                      >
                        Ver no mapa ({numbers.get(place.id)})
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => remove(place)}
                      disabled={busy === place.id}
                    >
                      {busy === place.id ? "Tirando…" : "Tirar da viagem"}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <aside className="itinerary-map">
            <p className="itinerary-map-label">
              {located.length > 0
                ? `${pluralize(located.length, "lugar", "lugares")} no mapa`
                : "Nenhum lugar com localização"}
            </p>
            <TripMap
              points={points}
              activeId={activeId}
              onSelect={setActiveId}
              label={`Mapa dos lugares de ${trip.title}`}
            />
            {located.length < places.length && (
              <p className="muted itinerary-map-note">
                {pluralize(
                  places.length - located.length,
                  "lugar sem coordenadas não aparece",
                  "lugares sem coordenadas não aparecem",
                )}{" "}
                no mapa.
              </p>
            )}
          </aside>
        </div>
      )}

      <Modal
        open={adding}
        onClose={() => setAdding(false)}
        title="Trazer da minha coleção"
        description={`Escolha os lugares que vão para “${trip.title}”.`}
      >
        <CollectionPicker
          linkedIds={new Set(places.map((place) => place.id))}
          onCancel={() => setAdding(false)}
          onConfirm={async (ids) => {
            await onAdd(ids);
            setAdding(false);
          }}
        />
      </Modal>
    </>
  );
}

function CollectionPicker({ linkedIds, onCancel, onConfirm }) {
  const [all, setAll] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    listPlaces({ signal: controller.signal })
      .then((data) => setAll(data))
      .catch((failure) => {
        if (!controller.signal.aborted) setLoadError(failure.message);
      });
    return () => controller.abort();
  }, []);

  if (loadError) {
    return (
      <p className="place-form-error" role="alert">
        Não foi possível carregar sua coleção. {loadError}
      </p>
    );
  }

  if (!all) {
    return <Feedback kind="loading" title="Carregando sua coleção…" />;
  }

  const available = all.filter((place) => !linkedIds.has(place.id));

  if (available.length === 0) {
    return (
      <div className="place-detail">
        <p className="muted">
          {all.length === 0
            ? "Sua coleção ainda está vazia."
            : "Todos os seus lugares já estão nesta viagem."}
        </p>
        <div className="modal-actions">
          <ButtonLink to="/lugares">Cadastrar em Meus lugares</ButtonLink>
        </div>
      </div>
    );
  }

  const visible = filterPlaces(available, { search });

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onConfirm(selected);
    } catch (failure) {
      setError(failure.message);
      setSaving(false);
    }
  }

  return (
    <form className="place-form" onSubmit={handleSubmit}>
      {error && (
        <p className="place-form-error" role="alert">
          {error}
        </p>
      )}

      <label className="places-search">
        <span className="sr-only">Buscar na coleção</span>
        <input
          type="search"
          placeholder="Buscar um lugar ou cidade"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          data-autofocus
        />
      </label>

      <fieldset className="place-trip-options picker-list" disabled={saving}>
        <legend className="sr-only">Lugares</legend>

        {visible.length === 0 && (
          <p className="muted">Nenhum lugar encontrado.</p>
        )}

        {visible.map((place) => (
          <label key={place.id} className="place-trip-option">
            <input
              type="checkbox"
              checked={selected.includes(place.id)}
              onChange={() =>
                setSelected((current) =>
                  current.includes(place.id)
                    ? current.filter((id) => id !== place.id)
                    : [...current, place.id],
                )
              }
            />
            <span>
              <strong>{place.name}</strong>
              <span className="muted">
                {" · "}
                {[place.city, categoryLabel(place.category)]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="modal-actions">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving || selected.length === 0}>
          {saving
            ? "Adicionando…"
            : selected.length
              ? `Adicionar ${pluralize(selected.length, "lugar", "lugares")}`
              : "Adicionar"}
        </Button>
      </div>
    </form>
  );
}
