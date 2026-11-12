// Dados simulados de viagens, no formato definido em docs/contratos-api.md.
// Usados por services/trips.js enquanto os endpoints de viagens não ficam prontos.

function activity(id, day, order, fields) {
  return {
    id,
    day,
    title: "",
    description: "",
    category: "other",
    start_time: null,
    end_time: null,
    duration_minutes: null,
    location_name: "",
    address: "",
    latitude: null,
    longitude: null,
    estimated_cost: "0.00",
    cost_type: "per_person",
    total_cost: "0.00",
    notes: "",
    image_url: "",
    order,
    ...fields,
  };
}

// Campos preenchidos pela geração de roteiro com IA, ainda vazios.
const noAiFields = {
  ai_summary: "",
  lodging_suggestions: [],
  cost_estimate: {},
  itinerary_generated_at: null,
};

function emptyDays(firstId, startDate, count) {
  const days = [];
  const start = new Date(`${startDate}T12:00:00`);

  for (let index = 0; index < count; index += 1) {
    const date = new Date(start);
    date.setDate(start.getDate() + index);

    days.push({
      id: firstId + index,
      date: date.toISOString().slice(0, 10),
      day_number: index + 1,
      title: "",
      notes: "",
      activities: [],
    });
  }

  return days;
}

// ---------------------------------------------------------------------------
// Lisboa com calma: viagem com roteiro preenchido (telas 01, 03 e 05)
// ---------------------------------------------------------------------------

const lisbonDays = emptyDays(101, "2027-05-12", 7);

lisbonDays[0].title = "Baixa e Alfama";
lisbonDays[0].activities = [
  activity(1001, 101, 1, {
    title: "Café e uma volta pela Baixa",
    description:
      "Comece o dia com um pastel de nata e caminhe pela Rua Augusta até a Praça do Comércio.",
    category: "gastronomy",
    start_time: "09:00:00",
    end_time: "10:30:00",
    duration_minutes: 90,
    location_name: "Baixa",
    address: "Rua Augusta, Lisboa",
    latitude: "38.710800",
    longitude: "-9.137700",
    estimated_cost: "60.00",
    cost_type: "per_person",
    total_cost: "240.00",
  }),
  activity(1002, 101, 2, {
    title: "Descobrir Alfama a pé",
    description:
      "Suba pelas ruelas do bairro mais antigo da cidade, sem pressa. Caminhada leve.",
    category: "culture",
    start_time: "11:00:00",
    end_time: "13:00:00",
    duration_minutes: 120,
    location_name: "Alfama",
    address: "Largo do Chafariz de Dentro, Lisboa",
    latitude: "38.711600",
    longitude: "-9.129500",
  }),
  activity(1003, 101, 3, {
    title: "Miradouro e tempo livre",
    description: "Vista do Tejo e tempo livre para explorar o entorno.",
    category: "sightseeing",
    start_time: "15:00:00",
    end_time: "16:00:00",
    duration_minutes: 60,
    location_name: "Miradouro de Santa Luzia",
    address: "Largo Santa Luzia, Lisboa",
    latitude: "38.711700",
    longitude: "-9.130200",
  }),
];

lisbonDays[1].title = "Belém";
lisbonDays[1].activities = [
  activity(1004, 102, 1, {
    title: "Mosteiro dos Jerónimos",
    category: "culture",
    start_time: "10:00:00",
    end_time: "11:30:00",
    duration_minutes: 90,
    location_name: "Mosteiro dos Jerónimos",
    address: "Praça do Império, Lisboa",
    latitude: "38.697900",
    longitude: "-9.206700",
    estimated_cost: "18.00",
    cost_type: "per_person",
    total_cost: "72.00",
  }),
  activity(1005, 102, 2, {
    title: "Pastéis de Belém",
    category: "gastronomy",
    start_time: "12:00:00",
    end_time: "12:45:00",
    duration_minutes: 45,
    location_name: "Pastéis de Belém",
    address: "Rua de Belém 84, Lisboa",
    latitude: "38.697500",
    longitude: "-9.203200",
    estimated_cost: "40.00",
    cost_type: "total",
    total_cost: "40.00",
  }),
];

lisbonDays[4].title = "Um dia em Sintra";
lisbonDays[4].notes = "Pegar o trem cedo na estação do Rossio.";
lisbonDays[4].activities = [
  activity(1006, 105, 1, {
    title: "Palácio da Pena",
    category: "culture",
    start_time: "10:00:00",
    end_time: "12:30:00",
    duration_minutes: 150,
    location_name: "Palácio da Pena",
    address: "Estrada da Pena, Sintra",
    latitude: "38.787600",
    longitude: "-9.390600",
    estimated_cost: "20.00",
    cost_type: "per_person",
    total_cost: "80.00",
  }),
];

export const lisbonTrip = {
  id: 12,
  title: "Lisboa com calma",
  description: "7 dias para descobrir a cidade, sem pressa.",
  origin: "São Paulo, Brasil",
  destination: "Lisboa, Portugal",
  start_date: "2027-05-12",
  end_date: "2027-05-18",
  duration_days: 7,
  travelers_count: 4,
  budget: "32000.00",
  currency: "BRL",
  mode: "group",
  status: "planning",
  style: "intermediate",
  pace: "relaxed",
  transport: "plane",
  interests: ["gastronomy", "culture"],
  cover_image_url: "",
  created_at: "2026-11-10T14:20:00-03:00",
  updated_at: "2026-11-12T09:05:00-03:00",
  ai_summary: "Lisboa sem pressa, entre cultura, miradouros e boa comida.",
  lodging_suggestions: [
    {
      name: "Hotel Lisboa Centro",
      area: "Baixa",
      description: "Perto do metrô e das principais atrações.",
      price_per_night: "650.00",
      currency: "BRL",
      latitude: "38.710000",
      longitude: "-9.140000",
    },
  ],
  cost_estimate: {
    currency: "BRL",
    transport: "16000.00",
    lodging: "8400.00",
    food: "4200.00",
    activities: "3400.00",
    total: "32000.00",
    per_person: "8000.00",
    within_budget: true,
    notes: "Valores aproximados.",
  },
  itinerary_generated_at: "2026-11-12T09:05:00-03:00",
  days: lisbonDays,
};

// ---------------------------------------------------------------------------
// Fim de semana no Rio: viagem sem roteiro ainda
// ---------------------------------------------------------------------------

export const rioTrip = {
  id: 13,
  title: "Fim de semana no Rio",
  description: "",
  origin: "São Paulo, Brasil",
  destination: "Rio de Janeiro, Brasil",
  start_date: "2027-02-20",
  end_date: "2027-02-23",
  duration_days: 4,
  travelers_count: 2,
  budget: "4000.00",
  currency: "BRL",
  mode: "group",
  status: "planning",
  style: "intermediate",
  pace: "moderate",
  transport: "plane",
  interests: ["beach", "gastronomy"],
  cover_image_url: "",
  created_at: "2026-11-11T10:00:00-03:00",
  updated_at: "2026-11-11T10:00:00-03:00",
  ...noAiFields,
  days: emptyDays(201, "2027-02-20", 4),
};

// ---------------------------------------------------------------------------
// Férias em grupo: destino ainda não escolhido
// ---------------------------------------------------------------------------

export const groupTrip = {
  id: 14,
  title: "Férias em grupo",
  description: "",
  origin: "São Paulo, Brasil",
  destination: "",
  start_date: "2027-07-10",
  end_date: "2027-07-17",
  duration_days: 8,
  travelers_count: 4,
  budget: null,
  currency: "BRL",
  mode: "group",
  status: "planning",
  style: "",
  pace: "",
  transport: "",
  interests: [],
  cover_image_url: "",
  created_at: "2026-11-11T18:30:00-03:00",
  updated_at: "2026-11-11T18:30:00-03:00",
  ...noAiFields,
  days: emptyDays(301, "2027-07-10", 8),
};

// ---------------------------------------------------------------------------
// Uma viagem já realizada (aba "Realizadas")
// ---------------------------------------------------------------------------

export const pastTrip = {
  id: 9,
  title: "Serra Gaúcha",
  description: "",
  origin: "São Paulo, Brasil",
  destination: "Gramado, Brasil",
  start_date: "2026-07-03",
  end_date: "2026-07-06",
  duration_days: 4,
  travelers_count: 2,
  budget: "5000.00",
  currency: "BRL",
  mode: "solo",
  status: "completed",
  style: "comfort",
  pace: "relaxed",
  transport: "plane",
  interests: ["gastronomy", "nature"],
  cover_image_url: "",
  created_at: "2026-05-02T09:00:00-03:00",
  updated_at: "2026-07-07T20:00:00-03:00",
  ...noAiFields,
  days: emptyDays(901, "2026-07-03", 4),
};

export const mockTrips = [pastTrip, rioTrip, lisbonTrip, groupTrip];

// Atividades que a "IA simulada" usa para preencher dias vazios.
export const mockGeneratedActivities = [
  {
    title: "Café da manhã em um lugar local",
    category: "gastronomy",
    start_time: "09:00:00",
    end_time: "10:00:00",
    duration_minutes: 60,
    estimated_cost: "50.00",
    cost_type: "per_person",
  },
  {
    title: "Passeio pelo centro histórico",
    category: "culture",
    start_time: "10:30:00",
    end_time: "13:00:00",
    duration_minutes: 150,
    estimated_cost: "0.00",
    cost_type: "per_person",
  },
  {
    title: "Fim de tarde com vista",
    category: "sightseeing",
    start_time: "17:00:00",
    end_time: "18:30:00",
    duration_minutes: 90,
    estimated_cost: "0.00",
    cost_type: "per_person",
  },
];

// Hospedagem que a "IA simulada" sugere ao gerar um roteiro.
export const mockLodgingSuggestions = [
  {
    name: "Hotel no centro",
    area: "Centro",
    description: "Bem localizado, perto do transporte público.",
    price_per_night: "600.00",
    currency: "BRL",
    latitude: null,
    longitude: null,
  },
];

// Opções que a "IA simulada" devolve em suggestDestinations().
export const mockDestinationSuggestions = [
  {
    destination: "Lisboa, Portugal",
    summary: "Cultura, boa comida e dias para caminhar sem pressa.",
    reasons: [
      "Combina com interesse por gastronomia e cultura",
      "Cidade compacta, boa para conhecer a pé",
    ],
    estimated_cost_per_person: "8000.00",
    currency: "BRL",
    best_for: ["culture", "gastronomy"],
  },
  {
    destination: "Rio de Janeiro, Brasil",
    summary: "Praia e cidade no mesmo roteiro.",
    reasons: ["Praias famosas", "Sem voo internacional"],
    estimated_cost_per_person: "3500.00",
    currency: "BRL",
    best_for: ["beach", "nature"],
  },
  {
    destination: "Sintra, Portugal",
    summary: "Natureza e palácios a poucos minutos de Lisboa.",
    reasons: ["Trilhas e paisagens", "Patrimônio histórico"],
    estimated_cost_per_person: "7500.00",
    currency: "BRL",
    best_for: ["nature", "culture", "sightseeing"],
  },
];
