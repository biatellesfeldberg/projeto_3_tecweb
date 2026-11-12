// Acesso aos lugares salvos ("Meus lugares") e aos lugares de cada viagem.
// Contratos: docs/contratos-api.md, seção "Lugares salvos".
//
// Os erros seguem o padrão de services/trips.js: as funções lançam ApiError,
// com message, fields (erros por campo) e status.

import { apiRequest } from "./trips";

export function listPlaces({ signal } = {}) {
  return apiRequest("places/", { signal });
}

export function getPlace(placeId, { signal } = {}) {
  return apiRequest(`places/${placeId}/`, { signal });
}

export function createPlace(data) {
  return apiRequest("places/", {
    method: "POST",
    data,
  });
}

export function updatePlace(placeId, data) {
  return apiRequest(`places/${placeId}/`, {
    method: "PATCH",
    data,
  });
}

export function deletePlace(placeId) {
  return apiRequest(`places/${placeId}/`, {
    method: "DELETE",
  });
}

export function listTripPlaces(tripId, { signal } = {}) {
  return apiRequest(`trips/${tripId}/places/`, { signal });
}

export function addPlacesToTrip(tripId, placeIds) {
  return apiRequest(`trips/${tripId}/places/`, {
    method: "POST",
    data: { place_ids: placeIds },
  });
}

export function removePlaceFromTrip(tripId, placeId) {
  return apiRequest(`trips/${tripId}/places/${placeId}/`, {
    method: "DELETE",
  });
}
