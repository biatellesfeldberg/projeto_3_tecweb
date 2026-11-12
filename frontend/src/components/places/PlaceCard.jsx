import { categoryLabel } from "../../utils/places";

export function PlaceCover({ place, className = "" }) {
  return (
    <div
      className={`place-cover place-cover--${place.category} ${className}`}
      aria-hidden="true"
    >
      <span className="place-cover-initial">
        {place.name.trim().charAt(0).toUpperCase()}
      </span>

      {place.image_url && (
        <img
          src={place.image_url}
          alt=""
          loading="lazy"
          onError={(event) => {
            event.currentTarget.hidden = true;
          }}
        />
      )}
    </div>
  );
}

export function placeTripsText(place) {
  const [first, ...others] = place.trips;

  if (!first) {
    return "Ainda sem viagem";
  }

  if (others.length === 0) {
    return `Salvo para ${first.title}`;
  }

  return `Salvo para ${first.title} e mais ${others.length}`;
}

export default function PlaceCard({
  place,
  selected = false,
  onToggle,
  onOpen,
}) {
  const location = [place.city, categoryLabel(place.category)]
    .filter(Boolean)
    .join(" · ");

  return (
    <li className={`place-item ${selected ? "is-selected" : ""}`}>
      <article className="place-card">
        <PlaceCover place={place} />

        <div className="place-card-body">
          <h2>
            <button
              type="button"
              className="place-open"
              onClick={() => onOpen(place)}
            >
              {place.name}
            </button>
          </h2>

          <p className="muted">{location}</p>
        </div>

        {onToggle && (
          <label className="place-select">
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggle(place.id)}
            />
            <span className="sr-only">Selecionar {place.name}</span>
          </label>
        )}
      </article>

      <p
        className={`place-trips ${
          place.trips.length ? "" : "is-empty"
        }`}
      >
        {placeTripsText(place)}
      </p>
    </li>
  );
}
