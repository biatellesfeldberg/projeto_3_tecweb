export const tripStatuses = [
  ["planning", "Em planejamento"],
  ["upcoming", "Próximas"],
  ["completed", "Realizadas"],
];

export const travelStyles = [
  ["economic", "Econômico"],
  ["intermediate", "Intermediário"],
  ["comfort", "Conforto"],
];

export const travelPaces = [
  ["relaxed", "Tranquilo"],
  ["moderate", "Moderado"],
  ["intense", "Intenso"],
];

export const transports = [
  ["plane", "Avião"],
  ["car", "Carro"],
  ["bus", "Ônibus"],
  ["train", "Trem"],
  ["other", "Outro"],
];

export const travelInterests = [
  ["beach", "Praia"],
  ["nature", "Natureza"],
  ["gastronomy", "Gastronomia"],
  ["adventure", "Aventura"],
  ["culture", "Cultura"],
  ["shopping", "Compras"],
  ["nightlife", "Vida noturna"],
  ["sightseeing", "Paisagens"],
];

export function initialTrip(profile) {
  return {
    title: "",
    origin: profile.home_city || "",
    destination: "",
    undecided: false,
    start_date: "",
    end_date: "",
    travelers_count: "1",
    budget: "",
    mode: "solo",
    style: profile.style || "",
    pace: profile.pace || "",
    transport: "",
    interests: [...(profile.interests || [])],
  };
}

function dateValue(value) {
  if (!/^(?!0000)\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null;
  }

  const date = new Date(`${value}T00:00:00Z`);

  if (
    !Number.isFinite(date.getTime()) ||
    date.toISOString().slice(0, 10) !== value
  ) {
    return null;
  }

  return date.getTime();
}

export function normalizeBudget(value) {
  const text = value.trim();

  if (!text) {
    return null;
  }

  let decimal;

  if (/^\d{1,3}(\.\d{3})+(,\d{1,2})?$/.test(text)) {
    decimal = text.replaceAll(".", "").replace(",", ".");
  } else if (/^\d+([.,]\d{1,2})?$/.test(text)) {
    decimal = text.replace(",", ".");
  } else {
    throw new Error(
      "Informe um valor positivo ou zero, com até duas casas decimais.",
    );
  }

  const [whole, fraction = ""] = decimal.split(".");
  const normalized = whole.replace(/^0+(?=\d)/, "");

  if (normalized.length > 10) {
    throw new Error(
      "O orçamento deve ser menor que R$ 10 bilhões.",
    );
  }

  return `${normalized}.${fraction.padEnd(2, "0")}`;
}

export function validateTrip(form) {
  const errors = {};

  const requiredTexts = [
    ["title", "o nome da viagem"],
    ["origin", "a cidade de origem"],
  ];

  for (const [name, label] of requiredTexts) {
    if (!form[name].trim()) {
      errors[name] = `Informe ${label}.`;
    } else if (form[name].trim().length > 120) {
      errors[name] = "Use até 120 caracteres.";
    }
  }

  if (
    !form.undecided &&
    form.destination.trim().length > 120
  ) {
    errors.destination = "Use até 120 caracteres.";
  }

  const start = dateValue(form.start_date);
  const end = dateValue(form.end_date);

  if (start === null) {
    errors.start_date =
      "Informe uma data de início válida.";
  }

  if (end === null) {
    errors.end_date =
      "Informe uma data de término válida.";
  }

  if (start !== null && end !== null) {
    if (end < start) {
      errors.end_date =
        "O término deve ser igual ou posterior ao início.";
    } else if ((end - start) / 86400000 + 1 > 60) {
      errors.end_date =
        "A viagem pode ter no máximo 60 dias.";
    }
  }

  if (
    !/^\d+$/.test(form.travelers_count) ||
    Number(form.travelers_count) < 1 ||
    Number(form.travelers_count) > 50
  ) {
    errors.travelers_count =
      "Informe um número inteiro de 1 a 50 viajantes.";
  }

  try {
    normalizeBudget(form.budget);
  } catch (error) {
    errors.budget = error.message;
  }

  return errors;
}

export function tripPayload(form) {
  return {
    title: form.title.trim(),
    origin: form.origin.trim(),

    destination: form.undecided
      ? ""
      : form.destination.trim(),

    start_date: form.start_date,
    end_date: form.end_date,
    travelers_count: Number(form.travelers_count),
    budget: normalizeBudget(form.budget),
    currency: "BRL",
    mode: form.mode,
    style: form.style,
    pace: form.pace,
    transport: form.transport,
    interests: [...form.interests],
    status: "planning",
  };
}

export function formatTripDate(value) {
  const date = dateValue(value);

  if (date === null) {
    return "Data não informada";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date));
}

export function formatTripBudget(
  value,
  currency = "BRL",
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "Orçamento não informado";
  }

  try {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency,
    }).format(Number(value));
  } catch {
    return `${currency} ${Number(value).toLocaleString("pt-BR")}`;
  }
}