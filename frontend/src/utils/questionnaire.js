import {
  normalizeBudget,
  travelPaces,
} from "./tripForm";

export const questionnaireSelects = [
  [
    "landscape",
    "Paisagem preferida",
    [
      ["beach", "Praia"],
      ["mountain", "Montanha"],
      ["city", "Cidade"],
      ["nature", "Natureza"],
      ["any", "Sem preferência"],
    ],
  ],
  [
    "pace",
    "Ritmo da viagem",
    travelPaces,
  ],
  [
    "gastronomy_importance",
    "Importância da gastronomia",
    [
      ["1", "1 — Pouca"],
      ["2", "2"],
      ["3", "3 — Média"],
      ["4", "4"],
      ["5", "5 — Muita"],
    ],
  ],
  [
    "destination_preference",
    "Tipo de destino",
    [
      ["any", "Sem preferência"],
      ["domestic", "Nacional"],
      ["international", "Internacional"],
    ],
  ],
  [
    "climate",
    "Clima preferido",
    [
      ["warm", "Quente"],
      ["mild", "Ameno"],
      ["cold", "Frio"],
      ["any", "Sem preferência"],
    ],
  ],
  [
    "accommodation",
    "Hospedagem preferida",
    [
      ["hostel", "Hostel"],
      ["hotel", "Hotel"],
      ["apartment", "Apartamento"],
      ["resort", "Resort"],
      ["any", "Sem preferência"],
    ],
  ],
];

export function initialQuestionnaire(answers, trip) {
  return {
    ...Object.fromEntries(
      questionnaireSelects.map(([key]) => [
        key,
        String(answers?.[key] ?? ""),
      ]),
    ),
    max_budget: String(
      answers?.max_budget ?? "",
    ),
    days: String(
      answers?.days ?? trip.duration_days ?? "",
    ),
    interests: [
      ...(answers?.interests || []),
    ],
    avoided_destinations: (
      answers?.avoided_destinations || []
    ).join("\n"),
    notes: answers?.notes || "",
  };
}

export function questionnairePayload(form) {
  const errors = {};

  for (const [key, , options] of questionnaireSelects) {
    if (
      !options.some(
        ([value]) => value === form[key],
      )
    ) {
      errors[key] = "Escolha uma opção.";
    }
  }

  let budget;

  try {
    budget = normalizeBudget(form.max_budget);

    if (!budget || Number(budget) <= 0) {
      throw new Error();
    }
  } catch {
    errors.max_budget =
      "Informe um valor maior que zero, com até duas casas decimais.";
  }

  if (
    !/^\d+$/.test(form.days) ||
    Number(form.days) < 1 ||
    Number(form.days) > 60
  ) {
    errors.days =
      "Informe um número inteiro de 1 a 60.";
  }

  if (!form.interests.length) {
    errors.interests =
      "Selecione pelo menos um interesse.";
  }

  const avoided = [
    ...new Set(
      form.avoided_destinations
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  ];

  if (
    avoided.length > 20 ||
    avoided.some(
      (value) => value.length > 120,
    )
  ) {
    errors.avoided_destinations =
      "Use até 20 destinos, um por linha, com até 120 caracteres cada.";
  }

  if (form.notes.length > 500) {
    errors.notes =
      "Use até 500 caracteres.";
  }

  return {
    errors,
    payload: {
      ...Object.fromEntries(
        questionnaireSelects.map(([key]) => [
          key,
          form[key],
        ]),
      ),
      max_budget: budget,
      days: Number(form.days),
      gastronomy_importance: Number(
        form.gastronomy_importance,
      ),
      interests: form.interests,
      avoided_destinations: avoided,
      notes: form.notes.trim(),
    },
  };
}

export const compatibilityLabels = {
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export const personName = (user) =>
  [
    user.first_name,
    user.last_name,
  ]
    .filter(Boolean)
    .join(" ") || "Integrante";

export const formatScore = (value) =>
  Number(value).toLocaleString(
    "pt-BR",
    { maximumFractionDigits: 1 },
  );