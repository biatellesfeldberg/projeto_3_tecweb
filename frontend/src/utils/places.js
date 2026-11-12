// Opções e funções auxiliares dos lugares salvos.

// Mesmas chaves da categoria da atividade (docs/contratos-api.md).
export const placeCategories = [
  ["gastronomy", "Gastronomia"],
  ["culture", "Cultura"],
  ["nature", "Natureza"],
  ["beach", "Praia"],
  ["sightseeing", "Paisagem"],
  ["shopping", "Compras"],
  ["nightlife", "Vida noturna"],
  ["adventure", "Aventura"],
  ["lodging", "Hospedagem"],
  ["transport", "Deslocamento"],
  ["free_time", "Tempo livre"],
  ["other", "Outro"],
];

const categoryLabels = Object.fromEntries(placeCategories);

export function categoryLabel(value) {
  return categoryLabels[value] || "Outro";
}

// Texto sem acentos e em minúsculas, para a busca encontrar "sao paulo"
// em "São Paulo".
export function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

export function filterPlaces(places, { search, city, category, trip }) {
  const terms = normalizeText(search).split(/\s+/).filter(Boolean);
  const cityKey = normalizeText(city);

  return places.filter((place) => {
    if (category && place.category !== category) {
      return false;
    }

    if (cityKey && normalizeText(place.city) !== cityKey) {
      return false;
    }

    if (trip === "none" && place.trips.length > 0) {
      return false;
    }

    if (
      trip &&
      trip !== "none" &&
      !place.trips.some((item) => String(item.id) === String(trip))
    ) {
      return false;
    }

    if (terms.length === 0) {
      return true;
    }

    const text = normalizeText(
      [
        place.name,
        place.city,
        place.country,
        place.address,
        place.description,
        place.notes,
        categoryLabel(place.category),
      ].join(" "),
    );

    return terms.every((term) => text.includes(term));
  });
}

// Cidades da coleção, das mais frequentes para as menos frequentes.
export function placeCities(places) {
  const counts = new Map();

  for (const place of places) {
    const city = place.city.trim();
    if (!city) continue;

    const key = normalizeText(city);
    const current = counts.get(key);
    counts.set(key, {
      label: current?.label || city,
      count: (current?.count || 0) + 1,
    });
  }

  return [...counts.values()]
    .sort(
      (a, b) =>
        b.count - a.count || a.label.localeCompare(b.label, "pt-BR"),
    )
    .map((item) => item.label);
}

export function hasCoordinates(place) {
  return (
    place.latitude !== null &&
    place.latitude !== "" &&
    place.longitude !== null &&
    place.longitude !== "" &&
    Number.isFinite(Number(place.latitude)) &&
    Number.isFinite(Number(place.longitude))
  );
}

export function mapLink(place) {
  if (hasCoordinates(place)) {
    const lat = Number(place.latitude);
    const lon = Number(place.longitude);
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`;
  }

  const query = [place.address, place.name, place.city, place.country]
    .filter(Boolean)
    .join(", ");

  return query
    ? `https://www.openstreetmap.org/search?query=${encodeURIComponent(query)}`
    : "";
}

// ---------------------------------------------------------------------------
// Formulário
// ---------------------------------------------------------------------------

export function emptyPlaceForm() {
  return {
    name: "",
    city: "",
    country: "",
    category: "other",
    description: "",
    notes: "",
    address: "",
    latitude: "",
    longitude: "",
    image_url: "",
    trip_ids: [],
  };
}

export function placeToForm(place) {
  return {
    name: place.name,
    city: place.city,
    country: place.country,
    category: place.category,
    description: place.description,
    notes: place.notes,
    address: place.address,
    latitude: place.latitude ?? "",
    longitude: place.longitude ?? "",
    image_url: place.image_url,
    trip_ids: place.trips.map((trip) => trip.id),
  };
}

function coordinate(value) {
  const text = String(value).trim().replace(",", ".");
  return text === "" ? null : Number(text);
}

export function validatePlace(form) {
  const errors = {};

  if (!form.name.trim()) {
    errors.name = "Dê um nome ao lugar.";
  }

  const latitude = coordinate(form.latitude);
  const longitude = coordinate(form.longitude);

  if ((latitude === null) !== (longitude === null)) {
    errors.latitude =
      "Informe a latitude e a longitude juntas, ou deixe as duas vazias.";
  } else if (latitude !== null) {
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      errors.latitude = "A latitude deve ficar entre -90 e 90.";
    }

    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      errors.longitude = "A longitude deve ficar entre -180 e 180.";
    }
  }

  const imageUrl = form.image_url.trim();
  if (imageUrl && !/^https?:\/\/\S+$/i.test(imageUrl)) {
    errors.image_url = "Use um endereço que comece com http:// ou https://.";
  }

  return errors;
}

export function placePayload(form) {
  const latitude = coordinate(form.latitude);
  const longitude = coordinate(form.longitude);

  return {
    name: form.name.trim(),
    city: form.city.trim(),
    country: form.country.trim(),
    category: form.category,
    description: form.description.trim(),
    notes: form.notes.trim(),
    address: form.address.trim(),
    latitude: latitude === null ? null : latitude.toFixed(6),
    longitude: longitude === null ? null : longitude.toFixed(6),
    image_url: form.image_url.trim(),
    trip_ids: form.trip_ids,
  };
}

export function pluralize(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`;
}
