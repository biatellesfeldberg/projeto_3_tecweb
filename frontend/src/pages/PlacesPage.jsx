import { useCallback, useEffect, useMemo, useState } from "react";

import { Navigate, useSearchParams } from "react-router-dom";

import { Button, PageHeading } from "../components/ui";
import Feedback from "../components/Feedback";
import PlaceCard from "../components/places/PlaceCard";
import PlaceFormDialog from "../components/places/PlaceFormDialog";
import PlaceDetailDialog from "../components/places/PlaceDetailDialog";
import AddToTripDialog from "../components/places/AddToTripDialog";

import { useAuth } from "../contexts/AuthContext";
import {
  addPlacesToTrip,
  createPlace,
  deletePlace,
  listPlaces,
  removePlaceFromTrip,
  updatePlace,
} from "../services/places";
import { listTrips } from "../services/trips";

import {
  filterPlaces,
  placeCategories,
  placeCities,
  pluralize,
} from "../utils/places";

import "./places.css";

// Quantas cidades aparecem como atalho de filtro.
const MAX_CITY_CHIPS = 6;

export default function PlacesPage() {
  const { user, isRestoring, expireSession } = useAuth();
  const userId = user?.id;

  // Filtros ficam na URL: dá para voltar, recarregar e compartilhar o link.
  const [params, setParams] = useSearchParams();
  const filters = {
    search: params.get("busca") || "",
    city: params.get("cidade") || "",
    category: params.get("categoria") || "",
    trip: params.get("viagem") || "",
  };

  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  const [trips, setTrips] = useState([]);
  const [tripsError, setTripsError] = useState("");

  const [selected, setSelected] = useState(() => new Set());
  const [dialog, setDialog] = useState(null);
  const [notice, setNotice] = useState("");

  const handleFailure = useCallback(
    (failure) => {
      if (failure.status === 401) {
        expireSession();
      }
      throw failure;
    },
    [expireSession],
  );

  // Lugares
  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();
    setLoading(true);
    setError("");

    listPlaces({ signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        if (!Array.isArray(data)) {
          throw new Error("Não foi possível interpretar a lista de lugares.");
        }
        setPlaces(data);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        if (failure.status === 401) {
          expireSession();
        } else {
          setError(failure.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [userId, retry, expireSession]);

  // Viagens (para vincular lugares). Uma falha aqui não impede a página.
  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();
    setTripsError("");

    listTrips({ signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setTrips(Array.isArray(data) ? data : []);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        if (failure.status === 401) {
          expireSession();
        } else {
          setTripsError(failure.message);
        }
      });

    return () => controller.abort();
  }, [userId, retry, expireSession]);

  const activeTrips = useMemo(
    () =>
      trips
        .filter((trip) => trip.status !== "completed")
        .sort((a, b) => a.start_date.localeCompare(b.start_date)),
    [trips],
  );

  const cities = useMemo(
    () => placeCities(places).slice(0, MAX_CITY_CHIPS),
    [places],
  );

  const visible = useMemo(
    () => filterPlaces(places, filters),
    [places, filters.search, filters.city, filters.category, filters.trip],
  );

  const filtering = Object.values(filters).some(Boolean);

  if (isRestoring) {
    return <Feedback kind="loading" title="Verificando sua sessão…" />;
  }

  if (!user) {
    return <Navigate to="/entrar" replace />;
  }

  // -------------------------------------------------------------------------
  // Filtros e seleção
  // -------------------------------------------------------------------------

  function setFilter(key, value) {
    const next = new URLSearchParams(params);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setParams(next, { replace: true });
  }

  function clearFilters() {
    setParams({}, { replace: true });
  }

  function toggleSelected(placeId) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(placeId)) {
        next.delete(placeId);
      } else {
        next.add(placeId);
      }
      return next;
    });
  }

  const visibleIds = visible.map((place) => place.id);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

  function toggleAllVisible() {
    setSelected((current) => {
      const next = new Set(current);
      for (const id of visibleIds) {
        if (allVisibleSelected) {
          next.delete(id);
        } else {
          next.add(id);
        }
      }
      return next;
    });
  }

  // -------------------------------------------------------------------------
  // Ações
  // -------------------------------------------------------------------------

  function replacePlaces(updated) {
    const byId = new Map(updated.map((place) => [place.id, place]));
    setPlaces((current) =>
      current.map((place) => byId.get(place.id) || place),
    );
  }

  const detailPlace =
    dialog?.type === "detail"
      ? places.find((place) => place.id === dialog.placeId) || null
      : null;

  const editingPlace =
    dialog?.type === "edit"
      ? places.find((place) => place.id === dialog.placeId) || null
      : null;

  async function handleCreate(payload) {
    const place = await createPlace(payload).catch(handleFailure);
    setPlaces((current) => [place, ...current]);
    setDialog(null);
    setNotice(`“${place.name}” foi adicionado à sua coleção.`);
  }

  async function handleUpdate(payload) {
    const place = await updatePlace(editingPlace.id, payload).catch(
      handleFailure,
    );
    replacePlaces([place]);
    setDialog({ type: "detail", placeId: place.id });
    setNotice(`“${place.name}” foi atualizado.`);
  }

  async function handleDelete(place) {
    await deletePlace(place.id).catch(handleFailure);
    setPlaces((current) => current.filter((item) => item.id !== place.id));
    setSelected((current) => {
      const next = new Set(current);
      next.delete(place.id);
      return next;
    });
    setDialog(null);
    setNotice(`“${place.name}” foi excluído.`);
  }

  async function handleRemoveFromTrip(place, trip) {
    await removePlaceFromTrip(trip.id, place.id).catch(handleFailure);
    replacePlaces([
      {
        ...place,
        trips: place.trips.filter((item) => item.id !== trip.id),
      },
    ]);
  }

  async function handleAddToTrip(trip) {
    const ids = [...selected];
    const tripPlaces = await addPlacesToTrip(trip.id, ids).catch(
      handleFailure,
    );
    replacePlaces(tripPlaces);
    setSelected(new Set());
    setDialog(null);
    setNotice(
      `${pluralize(ids.length, "lugar adicionado", "lugares adicionados")} a “${trip.title}”.`,
    );
  }

  // -------------------------------------------------------------------------
  // Tela
  // -------------------------------------------------------------------------

  const addButton = (
    <Button onClick={() => setDialog({ type: "create" })}>
      + Adicionar lugar
    </Button>
  );

  let content;

  if (error) {
    content = (
      <Feedback
        kind="error"
        title="Não foi possível carregar seus lugares."
        detail={error}
        onRetry={() => setRetry((value) => value + 1)}
      />
    );
  } else if (loading) {
    content = <Feedback kind="loading" title="Carregando seus lugares…" />;
  } else if (places.length === 0) {
    content = (
      <Feedback
        kind="empty"
        title="Sua coleção ainda está vazia."
        detail="Guarde aqui os lugares que você quer conhecer. Depois é só levá-los para o roteiro de uma viagem."
      >
        {addButton}
      </Feedback>
    );
  } else {
    content = (
      <>
        <div className="places-toolbar">
          <div className="places-filters">
            <label className="places-search">
              <span className="sr-only">Buscar um lugar ou cidade</span>
              <input
                type="search"
                placeholder="Buscar um lugar ou cidade"
                value={filters.search}
                onChange={(event) => setFilter("busca", event.target.value)}
              />
            </label>

            <label className="places-select">
              <span className="sr-only">Categoria</span>
              <select
                value={filters.category}
                onChange={(event) =>
                  setFilter("categoria", event.target.value)
                }
              >
                <option value="">Todas as categorias</option>
                {placeCategories.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="places-select">
              <span className="sr-only">Viagem</span>
              <select
                value={filters.trip}
                onChange={(event) => setFilter("viagem", event.target.value)}
              >
                <option value="">Todas as viagens</option>
                <option value="none">Ainda sem viagem</option>
                {trips.map((trip) => (
                  <option key={trip.id} value={trip.id}>
                    {trip.title}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {cities.length > 0 && (
            <div
              className="places-chips"
              role="group"
              aria-label="Filtrar por cidade"
            >
              <button
                type="button"
                className={`chip ${filters.city ? "" : "is-active"}`}
                aria-pressed={!filters.city}
                onClick={() => setFilter("cidade", "")}
              >
                Todas as cidades
              </button>

              {cities.map((city) => (
                <button
                  key={city}
                  type="button"
                  className={`chip ${
                    filters.city === city ? "is-active" : ""
                  }`}
                  aria-pressed={filters.city === city}
                  onClick={() =>
                    setFilter("cidade", filters.city === city ? "" : city)
                  }
                >
                  {city}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="places-summary">
          <p className="muted" role="status">
            {filtering
              ? `${pluralize(visible.length, "lugar encontrado", "lugares encontrados")} de ${places.length}`
              : pluralize(places.length, "lugar guardado", "lugares guardados")}
          </p>

          <div className="places-summary-actions">
            {filtering && (
              <Button variant="ghost" onClick={clearFilters}>
                Limpar filtros
              </Button>
            )}

            {visible.length > 0 && (
              <Button variant="ghost" onClick={toggleAllVisible}>
                {allVisibleSelected ? "Desmarcar todos" : "Selecionar todos"}
              </Button>
            )}
          </div>
        </div>

        {visible.length === 0 ? (
          <Feedback
            kind="empty"
            title="Nenhum lugar encontrado."
            detail="Tente outra busca ou limpe os filtros."
          >
            <Button variant="secondary" onClick={clearFilters}>
              Limpar filtros
            </Button>
          </Feedback>
        ) : (
          <ul className="places-grid">
            {visible.map((place) => (
              <PlaceCard
                key={place.id}
                place={place}
                selected={selected.has(place.id)}
                onToggle={toggleSelected}
                onOpen={(item) =>
                  setDialog({ type: "detail", placeId: item.id })
                }
              />
            ))}
          </ul>
        )}

        <aside
          className={`places-selection ${
            selected.size > 0 ? "is-active" : ""
          }`}
          aria-label="Lugares selecionados"
        >
          <div>
            <h2>
              {selected.size > 0
                ? pluralize(
                    selected.size,
                    "lugar selecionado",
                    "lugares selecionados",
                  )
                : "Já sabe quando quer ir?"}
            </h2>
            <p className="muted">
              {selected.size > 0
                ? "Escolha a viagem que vai receber esses lugares."
                : "Selecione seus lugares e leve todos para o roteiro de uma viagem."}
            </p>
          </div>

          <div className="places-selection-actions">
            {selected.size > 0 && (
              <Button variant="ghost" onClick={() => setSelected(new Set())}>
                Limpar seleção
              </Button>
            )}

            <Button
              onClick={() => setDialog({ type: "addToTrip" })}
              disabled={selected.size === 0}
            >
              Adicionar à viagem
            </Button>
          </div>
        </aside>
      </>
    );
  }

  return (
    <>
      <PageHeading
        eyebrow="Sua coleção"
        title="Lugares para guardar."
        description="O café que te indicaram, a praia que você quer conhecer, a próxima descoberta."
        action={places.length > 0 || loading || error ? addButton : null}
      />

      {notice && (
        <div className="places-notice">
          <Feedback kind="success" title={notice}>
            <Button variant="ghost" onClick={() => setNotice("")}>
              Fechar aviso
            </Button>
          </Feedback>
        </div>
      )}

      {content}

      <PlaceFormDialog
        open={dialog?.type === "create" || Boolean(editingPlace)}
        place={editingPlace}
        trips={activeTrips}
        onClose={() =>
          setDialog(
            editingPlace
              ? { type: "detail", placeId: editingPlace.id }
              : null,
          )
        }
        onSave={editingPlace ? handleUpdate : handleCreate}
      />

      <PlaceDetailDialog
        place={detailPlace}
        onClose={() => setDialog(null)}
        onEdit={(place) => setDialog({ type: "edit", placeId: place.id })}
        onDelete={handleDelete}
        onRemoveFromTrip={handleRemoveFromTrip}
      />

      <AddToTripDialog
        open={dialog?.type === "addToTrip"}
        count={selected.size}
        trips={activeTrips}
        tripsError={tripsError}
        onClose={() => setDialog(null)}
        onConfirm={handleAddToTrip}
      />
    </>
  );
}
