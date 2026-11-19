import { apiRequest } from "./trips";

export const getMyQuestionnaire = (tripId, options = {}) =>
  apiRequest(`trips/${tripId}/questionnaire/me/`, options);

export const saveMyQuestionnaire = (
  tripId,
  data,
  options = {},
) =>
  apiRequest(`trips/${tripId}/questionnaire/me/`, {
    ...options,
    method: "PUT",
    data,
  });

export const getQuestionnaireProgress = (
  tripId,
  options = {},
) =>
  apiRequest(
    `trips/${tripId}/questionnaire/progress/`,
    options,
  );

export const getGroupDestinations = (
  tripId,
  options = {},
) =>
  apiRequest(
    `trips/${tripId}/group-destinations/`,
    options,
  );

export const generateGroupDestinations = (
  tripId,
  data,
  options = {},
) =>
  apiRequest(`trips/${tripId}/group-destinations/`, {
    ...options,
    method: "POST",
    data,
  });