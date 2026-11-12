// Acesso às viagens, dias, atividades e geração de roteiro.
// Contratos: docs/contratos-api.md.
//
// Por padrão, usa o backend real.
// Para usar os mocks existentes:
// VITE_USE_MOCKS=true npm run dev

import { getToken } from "./auth";

import {
  mockDestinationSuggestions,
  mockGeneratedActivities,
  mockLodgingSuggestions,
  mockTrips,
} from "../mocks/trips";

export const USE_MOCKS =
  import.meta.env.VITE_USE_MOCKS === "true";

export class ApiError extends Error {
  constructor(message, fields = {}, status = 0) {
    super(message);
    this.fields = fields;
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Funções públicas
// ---------------------------------------------------------------------------

export function listTrips({
  status,
  signal,
  token,
} = {}) {
  if (USE_MOCKS) {
    return mock.listTrips(status);
  }

  const query = status
    ? `?status=${encodeURIComponent(status)}`
    : "";

  return apiRequest(`trips/${query}`, {
    signal,
    token,
  });
}

export function getTrip(tripId, { signal } = {}) {
  if (USE_MOCKS) {
    return mock.getTrip(tripId);
  }

  return apiRequest(`trips/${tripId}/`, {
    signal,
  });
}

export function createTrip(
  data,
  { signal, token } = {},
) {
  if (USE_MOCKS) {
    return mock.createTrip(data);
  }

  return apiRequest("trips/", {
    method: "POST",
    data,
    signal,
    token,
  });
}

export function updateTrip(tripId, data) {
  if (USE_MOCKS) {
    return mock.updateTrip(tripId, data);
  }

  return apiRequest(`trips/${tripId}/`, {
    method: "PATCH",
    data,
  });
}

export function deleteTrip(tripId) {
  if (USE_MOCKS) {
    return mock.deleteTrip(tripId);
  }

  return apiRequest(`trips/${tripId}/`, {
    method: "DELETE",
  });
}

export function duplicateTrip(tripId) {
  if (USE_MOCKS) {
    return mock.duplicateTrip(tripId);
  }

  return apiRequest(`trips/${tripId}/duplicate/`, {
    method: "POST",
  });
}

export function updateDay(tripId, dayId, data) {
  if (USE_MOCKS) {
    return mock.updateDay(tripId, dayId, data);
  }

  return apiRequest(
    `trips/${tripId}/days/${dayId}/`,
    {
      method: "PATCH",
      data,
    },
  );
}

export function createActivity(tripId, data) {
  if (USE_MOCKS) {
    return mock.createActivity(tripId, data);
  }

  return apiRequest(
    `trips/${tripId}/activities/`,
    {
      method: "POST",
      data,
    },
  );
}

export function updateActivity(
  tripId,
  activityId,
  data,
) {
  if (USE_MOCKS) {
    return mock.updateActivity(
      tripId,
      activityId,
      data,
    );
  }

  return apiRequest(
    `trips/${tripId}/activities/${activityId}/`,
    {
      method: "PATCH",
      data,
    },
  );
}

export function deleteActivity(
  tripId,
  activityId,
) {
  if (USE_MOCKS) {
    return mock.deleteActivity(
      tripId,
      activityId,
    );
  }

  return apiRequest(
    `trips/${tripId}/activities/${activityId}/`,
    {
      method: "DELETE",
    },
  );
}

export function reorderActivities(
  tripId,
  dayId,
  activityIds,
) {
  if (USE_MOCKS) {
    return mock.reorderActivities(
      tripId,
      dayId,
      activityIds,
    );
  }

  return apiRequest(
    `trips/${tripId}/days/${dayId}/reorder/`,
    {
      method: "POST",
      data: {
        activity_ids: activityIds,
      },
    },
  );
}

export function generateItinerary(
  tripId,
  {
    replaceExisting = true,
    extraInstructions = "",
  } = {},
) {
  const data = {
    replace_existing: replaceExisting,
    extra_instructions: extraInstructions,
  };

  if (USE_MOCKS) {
    return mock.generateItinerary(tripId, data);
  }

  return apiRequest(
    `trips/${tripId}/generate-itinerary/`,
    {
      method: "POST",
      data,
    },
  );
}

// Opções de destino para quem ainda não escolheu (nada é salvo).
// Devolve { suggestions: [...] }. Também pode demorar alguns segundos.
export function suggestDestinations(
  tripId,
  { extraInstructions = "" } = {},
) {
  const data = {
    extra_instructions: extraInstructions,
  };

  if (USE_MOCKS) {
    return mock.suggestDestinations(tripId, data);
  }

  return apiRequest(
    `trips/${tripId}/destination-suggestions/`,
    {
      method: "POST",
      data,
    },
  );
}

// ---------------------------------------------------------------------------
// Requisições reais à API
// ---------------------------------------------------------------------------

async function apiRequest(
  path,
  {
    method = "GET",
    data,
    signal,
    token = getToken(),
  } = {},
) {
  let response;

  try {
    response = await fetch(`/api/${path}`, {
      method,
      signal,

      headers: {
        Accept: "application/json",

        ...(data
          ? { "Content-Type": "application/json" }
          : {}),

        ...(token
          ? { Authorization: `Token ${token}` }
          : {}),
      },

      ...(data
        ? { body: JSON.stringify(data) }
        : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new ApiError(
      "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
    );
  }

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const fields = {};

    if (body && typeof body === "object") {
      for (const [key, value] of Object.entries(body)) {
        fields[key] = messages(value);
      }
    }

    throw new ApiError(
      fields.detail ||
        fields.non_field_errors ||
        (response.status >= 500
          ? "O servidor está indisponível. Tente novamente em instantes."
          : "Confira os campos informados e tente novamente."),
      fields,
      response.status,
    );
  }

  if (!body || typeof body !== "object") {
    throw new ApiError(
      "O servidor retornou uma resposta inesperada. Tente novamente.",
    );
  }

  return body;
}

function messages(value) {
  return value && typeof value === "object"
    ? Object.values(value).map(messages).join(" ")
    : String(value);
}

// ---------------------------------------------------------------------------
// Implementação simulada: usada apenas com USE_MOCKS = true
// ---------------------------------------------------------------------------

const db = {
  trips: structuredClone(mockTrips),
  nextId: 5000,
};

const wait = (ms = 400) =>
  new Promise((resolve) => setTimeout(resolve, ms));

const copy = (value) => structuredClone(value);

const now = () => new Date().toISOString();

function notFound() {
  return new ApiError(
    "Não encontrado.",
    { detail: "Não encontrado." },
    404,
  );
}

function invalid(fields) {
  const first = Object.values(fields)[0];

  return new ApiError(first, fields, 400);
}

function findTrip(tripId) {
  const trip = db.trips.find(
    (item) => item.id === Number(tripId),
  );

  if (!trip) {
    throw notFound();
  }

  return trip;
}

function findDay(trip, dayId) {
  const day = trip.days.find(
    (item) => item.id === Number(dayId),
  );

  if (!day) {
    throw notFound();
  }

  return day;
}

function findActivity(trip, activityId) {
  for (const day of trip.days) {
    const activity = day.activities.find(
      (item) => item.id === Number(activityId),
    );

    if (activity) {
      return { day, activity };
    }
  }

  throw notFound();
}

function summary(trip) {
  const {
    days,
    description,
    style,
    pace,
    transport,
    interests,
    ...rest
  } = trip;

  return rest;
}

function datesBetween(start, end) {
  const dates = [];

  const current = new Date(`${start}T12:00:00`);
  const last = new Date(`${end}T12:00:00`);

  while (current <= last) {
    dates.push(
      current.toISOString().slice(0, 10),
    );

    current.setDate(current.getDate() + 1);
  }

  return dates;
}

function validateDates(trip) {
  if (!trip.start_date || !trip.end_date) {
    throw invalid({
      start_date: "Informe as datas da viagem.",
    });
  }

  if (trip.end_date < trip.start_date) {
    throw invalid({
      end_date:
        "A data de término deve ser igual ou posterior à data de início.",
    });
  }
}

function syncDays(trip) {
  const dates = datesBetween(
    trip.start_date,
    trip.end_date,
  );

  const byDate = new Map(
    trip.days.map((day) => [day.date, day]),
  );

  trip.days = dates.map((date, index) => {
    const day = byDate.get(date) || {
      id: db.nextId++,
      date,
      title: "",
      notes: "",
      activities: [],
    };

    day.day_number = index + 1;

    return day;
  });

  trip.duration_days = dates.length;
}

function withTotal(trip, activity) {
  const cost = Number(
    activity.estimated_cost || 0,
  );

  const total =
    activity.cost_type === "per_person"
      ? cost * trip.travelers_count
      : cost;

  activity.total_cost = total.toFixed(2);

  return activity;
}

function sortActivities(day) {
  day.activities.sort(
    (a, b) =>
      a.order - b.order ||
      String(a.start_time).localeCompare(
        String(b.start_time),
      ),
  );
}

function normalizeTime(value) {
  if (!value) {
    return null;
  }

  return value.length === 5
    ? `${value}:00`
    : value;
}

const mock = {
  async listTrips(status) {
    await wait();

    return db.trips
      .filter(
        (trip) => !status || trip.status === status,
      )
      .sort((a, b) =>
        a.start_date.localeCompare(b.start_date),
      )
      .map((trip) => copy(summary(trip)));
  },

  async getTrip(tripId) {
    await wait();

    return copy(findTrip(tripId));
  },

  async createTrip(data) {
    await wait();

    if (!data.title) {
      throw invalid({
        title: "Este campo é obrigatório.",
      });
    }

    if (!data.origin) {
      throw invalid({
        origin: "Este campo é obrigatório.",
      });
    }

    const trip = {
      id: db.nextId++,
      title: data.title,
      description: data.description || "",
      origin: data.origin,
      destination: data.destination || "",
      start_date: data.start_date,
      end_date: data.end_date,
      duration_days: 0,

      travelers_count:
        Number(data.travelers_count) || 1,

      budget: data.budget ?? null,
      currency: data.currency || "BRL",
      mode: data.mode || "solo",
      status: data.status || "planning",
      style: data.style || "",
      pace: data.pace || "",
      transport: data.transport || "",
      interests: data.interests || [],
      cover_image_url: data.cover_image_url || "",
      created_at: now(),
      updated_at: now(),
      ai_summary: "",
      lodging_suggestions: [],
      cost_estimate: {},
      itinerary_generated_at: null,
      days: [],
    };

    validateDates(trip);
    syncDays(trip);

    db.trips.push(trip);

    return copy(trip);
  },

  async updateTrip(tripId, data) {
    await wait();

    const trip = findTrip(tripId);
    const updated = { ...trip, ...data };

    validateDates(updated);

    Object.assign(trip, data, {
      updated_at: now(),
    });

    syncDays(trip);

    trip.days.forEach((day) =>
      day.activities.forEach((activity) =>
        withTotal(trip, activity),
      ),
    );

    return copy(trip);
  },

  async deleteTrip(tripId) {
    await wait();

    findTrip(tripId);

    db.trips = db.trips.filter(
      (trip) => trip.id !== Number(tripId),
    );

    return null;
  },

  async duplicateTrip(tripId) {
    await wait();

    const original = findTrip(tripId);
    const trip = copy(original);

    trip.id = db.nextId++;
    trip.title =
      `${original.title.slice(0, 120 - 8)} (cópia)`;

    trip.status = "planning";
    trip.created_at = now();
    trip.updated_at = now();

    trip.days.forEach((day) => {
      day.id = db.nextId++;

      day.activities.forEach((activity) => {
        activity.id = db.nextId++;
        activity.day = day.id;
      });
    });

    db.trips.push(trip);

    return copy(trip);
  },

  async updateDay(tripId, dayId, data) {
    await wait();

    const day = findDay(
      findTrip(tripId),
      dayId,
    );

    if (data.title !== undefined) {
      day.title = data.title;
    }

    if (data.notes !== undefined) {
      day.notes = data.notes;
    }

    return copy(day);
  },

  async createActivity(tripId, data) {
    await wait();

    const trip = findTrip(tripId);

    if (!data.title) {
      throw invalid({
        title: "Este campo é obrigatório.",
      });
    }

    const day = trip.days.find(
      (item) => item.id === Number(data.day),
    );

    if (!day) {
      throw invalid({
        day: "Este dia não pertence a esta viagem.",
      });
    }

    const activity = withTotal(trip, {
      id: db.nextId++,
      description: "",
      category: "other",
      end_time: null,
      duration_minutes: null,
      location_name: "",
      address: "",
      latitude: null,
      longitude: null,
      estimated_cost: "0.00",
      cost_type: "per_person",
      notes: "",
      image_url: "",
      order: day.activities.length + 1,
      ...data,
      day: day.id,

      start_time: normalizeTime(data.start_time),
    });

    activity.end_time = normalizeTime(
      activity.end_time,
    );

    day.activities.push(activity);
    sortActivities(day);

    return copy(activity);
  },

  async updateActivity(
    tripId,
    activityId,
    data,
  ) {
    await wait();

    const trip = findTrip(tripId);

    const { day, activity } = findActivity(
      trip,
      activityId,
    );

    if (
      data.day !== undefined &&
      Number(data.day) !== day.id
    ) {
      const target = trip.days.find(
        (item) => item.id === Number(data.day),
      );

      if (!target) {
        throw invalid({
          day: "Este dia não pertence a esta viagem.",
        });
      }

      day.activities = day.activities.filter(
        (item) => item !== activity,
      );

      target.activities.push(activity);
      activity.order = target.activities.length;
    }

    Object.assign(activity, data, {
      day: activity.day,
    });

    if (data.day !== undefined) {
      activity.day = Number(data.day);
    }

    activity.start_time = normalizeTime(
      activity.start_time,
    );

    activity.end_time = normalizeTime(
      activity.end_time,
    );

    withTotal(trip, activity);
    trip.days.forEach(sortActivities);

    return copy(activity);
  },

  async deleteActivity(
    tripId,
    activityId,
  ) {
    await wait();

    const trip = findTrip(tripId);

    const { day, activity } = findActivity(
      trip,
      activityId,
    );

    day.activities = day.activities.filter(
      (item) => item !== activity,
    );

    return null;
  },

  async reorderActivities(
    tripId,
    dayId,
    activityIds,
  ) {
    await wait();

    const day = findDay(
      findTrip(tripId),
      dayId,
    );

    const current = day.activities
      .map((item) => item.id)
      .sort();

    const sent = [...activityIds]
      .map(Number)
      .sort();

    if (
      JSON.stringify(current) !==
      JSON.stringify(sent)
    ) {
      throw invalid({
        activity_ids:
          "Envie todas as atividades deste dia, sem repetir.",
      });
    }

    activityIds.forEach((id, index) => {
      day.activities.find(
        (item) => item.id === Number(id),
      ).order = index + 1;
    });

    sortActivities(day);

    return copy(day);
  },

  async generateItinerary(
    tripId,
    { replace_existing: replaceExisting },
  ) {
    await wait(1500);

    const trip = findTrip(tripId);

    if (!trip.destination) {
      throw invalid({
        destination:
          "Escolha um destino antes de gerar o roteiro.",
      });
    }

    const city = trip.destination.split(",")[0];

    trip.days.forEach((day) => {
      if (
        !replaceExisting &&
        day.activities.length > 0
      ) {
        return;
      }

      day.title =
        day.title ||
        `Dia ${day.day_number} em ${city}`;

      day.activities =
        mockGeneratedActivities.map(
          (template, index) =>
            withTotal(trip, {
              id: db.nextId++,
              day: day.id,
              description: "",
              location_name: city,
              address: "",
              latitude: null,
              longitude: null,
              notes: "",
              image_url: "",
              order: index + 1,
              ...template,
            }),
        );
    });

    const nights = Math.max(trip.duration_days - 1, 1);
    const lodging = Number(
      mockLodgingSuggestions[0].price_per_night,
    ) * nights;
    const activities = trip.days
      .flatMap((day) => day.activities)
      .reduce(
        (sum, activity) =>
          sum + Number(activity.total_cost || 0),
        0,
      );
    const food = 150 * trip.travelers_count * trip.duration_days;
    const transport = 2000 * trip.travelers_count;
    const total = transport + lodging + food + activities;

    trip.ai_summary =
      `Roteiro simulado para ${city}.`;
    trip.lodging_suggestions = copy(
      mockLodgingSuggestions,
    );
    trip.cost_estimate = {
      currency: trip.currency,
      transport: transport.toFixed(2),
      lodging: lodging.toFixed(2),
      food: food.toFixed(2),
      activities: activities.toFixed(2),
      total: total.toFixed(2),
      per_person: (
        total / trip.travelers_count
      ).toFixed(2),
      within_budget:
        trip.budget === null
          ? null
          : total <= Number(trip.budget),
      notes: "Valores simulados.",
    };
    trip.itinerary_generated_at = now();
    trip.updated_at = now();

    return copy(trip);
  },

  async suggestDestinations(tripId) {
    await wait(1000);

    const trip = findTrip(tripId);

    return {
      suggestions: copy(
        mockDestinationSuggestions,
      ).filter(
        (option) =>
          option.destination !== trip.destination,
      ),
    };
  },
};