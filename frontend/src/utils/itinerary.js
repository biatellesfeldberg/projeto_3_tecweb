// Formatação e formulário do roteiro diário (dias e atividades).
// Formatos dos dados: docs/contratos-api.md, seções "Viagens" e
// "Dias e atividades".

import { categoryLabel, hasCoordinates } from "./places";

export { categoryLabel, hasCoordinates };

export const costTypes = [
  ["per_person", "Por pessoa"],
  ["total", "Total do grupo"],
];

export const tripStatusLabels = {
  planning: "Em planejamento",
  upcoming: "Próxima",
  completed: "Realizada",
};

function utcDate(value) {
  // "2027-05-12" -> Date em UTC, para o fuso não trocar o dia.
  return new Date(`${value}T00:00:00Z`);
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// "Quarta, 12 de maio"
export function formatDayLong(value) {
  const date = utcDate(value);
  const weekday = new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    timeZone: "UTC",
  })
    .format(date)
    .replace("-feira", "");
  const rest = new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(date);

  return `${capitalize(weekday)}, ${rest}`;
}

// { day: "12", weekday: "qua" }
export function formatDayChip(value) {
  const date = utcDate(value);
  return {
    day: String(date.getUTCDate()),
    weekday: new Intl.DateTimeFormat("pt-BR", {
      weekday: "short",
      timeZone: "UTC",
    })
      .format(date)
      .replace(".", ""),
  };
}

// "12 a 18 mai 2027" (ou "28 abr a 2 mai 2027", "30 dez 2026 a 2 jan 2027")
export function formatDateRange(start, end) {
  const a = utcDate(start);
  const b = utcDate(end);
  const month = (date) =>
    new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" })
      .format(date)
      .replace(".", "");

  if (a.getUTCFullYear() !== b.getUTCFullYear()) {
    return `${a.getUTCDate()} ${month(a)} ${a.getUTCFullYear()} a ${b.getUTCDate()} ${month(b)} ${b.getUTCFullYear()}`;
  }

  if (a.getUTCMonth() !== b.getUTCMonth()) {
    return `${a.getUTCDate()} ${month(a)} a ${b.getUTCDate()} ${month(b)} ${b.getUTCFullYear()}`;
  }

  if (a.getUTCDate() === b.getUTCDate()) {
    return `${a.getUTCDate()} ${month(a)} ${a.getUTCFullYear()}`;
  }

  return `${a.getUTCDate()} a ${b.getUTCDate()} ${month(b)} ${b.getUTCFullYear()}`;
}

// "09:00:00" -> "09:00"
export function formatTime(value) {
  return value ? value.slice(0, 5) : "";
}

// 90 -> "1h30", 60 -> "1h", 45 -> "45 min"
export function formatDuration(minutes) {
  if (!minutes) return "";
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest ? `${hours}h${String(rest).padStart(2, "0")}` : `${hours}h`;
}

export function formatMoney(value, currency = "BRL") {
  const number = Number(value);
  try {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency,
      maximumFractionDigits: Number.isInteger(number) ? 0 : 2,
    }).format(number);
  } catch {
    return `${currency} ${number.toLocaleString("pt-BR")}`;
  }
}

// "R$ 60 / pessoa", "R$ 240 no total", "sem custo"
export function formatActivityCost(activity, currency) {
  const cost = Number(activity.estimated_cost);
  if (!cost) return "sem custo";
  const money = formatMoney(cost, currency);
  return activity.cost_type === "total"
    ? `${money} no total`
    : `${money} / pessoa`;
}

export function countActivities(trip) {
  return trip.days.reduce((sum, day) => sum + day.activities.length, 0);
}

// ---------------------------------------------------------------------------
// Formulário de atividade
// ---------------------------------------------------------------------------

export function emptyActivityForm(dayId) {
  return {
    day: dayId ? String(dayId) : "",
    title: "",
    category: "other",
    start_time: "",
    end_time: "",
    duration_minutes: "",
    location_name: "",
    address: "",
    latitude: "",
    longitude: "",
    estimated_cost: "",
    cost_type: "per_person",
    description: "",
    notes: "",
    image_url: "",
  };
}

export function activityToForm(activity) {
  return {
    day: String(activity.day),
    title: activity.title,
    category: activity.category,
    start_time: formatTime(activity.start_time),
    end_time: formatTime(activity.end_time),
    duration_minutes:
      activity.duration_minutes === null ? "" : String(activity.duration_minutes),
    location_name: activity.location_name,
    address: activity.address,
    latitude: activity.latitude ?? "",
    longitude: activity.longitude ?? "",
    estimated_cost: Number(activity.estimated_cost) ? activity.estimated_cost : "",
    cost_type: activity.cost_type,
    description: activity.description,
    notes: activity.notes,
    image_url: activity.image_url,
  };
}

// Um lugar salvo vira uma atividade já preenchida.
export function placeToActivityForm(place, dayId) {
  return {
    ...emptyActivityForm(dayId),
    title: place.name,
    category: place.category,
    location_name: place.name,
    address: [place.address, place.city].filter(Boolean).join(", "),
    latitude: place.latitude ?? "",
    longitude: place.longitude ?? "",
    description: place.description,
    notes: place.notes,
    image_url: place.image_url,
  };
}

function decimal(value) {
  const text = String(value).trim().replace(",", ".");
  return text === "" ? null : Number(text);
}

export function validateActivity(form) {
  const errors = {};

  if (!form.day) errors.day = "Escolha o dia.";
  if (!form.title.trim()) errors.title = "Dê um nome à atividade.";

  if (form.start_time && form.end_time && form.end_time < form.start_time) {
    errors.end_time = "O término deve ser depois do início.";
  }

  const duration = decimal(form.duration_minutes);
  if (
    duration !== null &&
    (!Number.isInteger(duration) || duration <= 0 || duration > 1440)
  ) {
    errors.duration_minutes = "Use minutos inteiros, entre 1 e 1440.";
  }

  const cost = decimal(form.estimated_cost);
  if (cost !== null && (!Number.isFinite(cost) || cost < 0)) {
    errors.estimated_cost = "Informe um valor igual ou maior que zero.";
  }

  const latitude = decimal(form.latitude);
  const longitude = decimal(form.longitude);
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

// Duração calculada pelos horários quando não for informada.
function durationFromTimes(start, end) {
  if (!start || !end) return null;
  const [h1, m1] = start.split(":").map(Number);
  const [h2, m2] = end.split(":").map(Number);
  const minutes = h2 * 60 + m2 - (h1 * 60 + m1);
  return minutes > 0 ? minutes : null;
}

export function activityPayload(form) {
  const latitude = decimal(form.latitude);
  const longitude = decimal(form.longitude);
  const cost = decimal(form.estimated_cost);
  const duration = decimal(form.duration_minutes);

  return {
    day: Number(form.day),
    title: form.title.trim(),
    category: form.category,
    start_time: form.start_time || null,
    end_time: form.end_time || null,
    duration_minutes:
      duration ?? durationFromTimes(form.start_time, form.end_time),
    location_name: form.location_name.trim(),
    address: form.address.trim(),
    latitude: latitude === null ? null : latitude.toFixed(6),
    longitude: longitude === null ? null : longitude.toFixed(6),
    estimated_cost: (cost ?? 0).toFixed(2),
    cost_type: form.cost_type,
    description: form.description.trim(),
    notes: form.notes.trim(),
    image_url: form.image_url.trim(),
  };
}
