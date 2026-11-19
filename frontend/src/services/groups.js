// S2-08: integrantes, convites e votações. Não chama APIs de IA.
import { apiRequest } from "./trips";

export const listMembers = (tripId, options = {}) =>
  apiRequest(`trips/${tripId}/members/`, options);

export const inviteMember = (tripId, userId, options = {}) =>
  apiRequest(`trips/${tripId}/members/`, {
    ...options,
    method: "POST",
    data: { user_id: userId },
  });

export const removeMember = (tripId, userId, options = {}) =>
  apiRequest(`trips/${tripId}/members/${userId}/`, {
    ...options,
    method: "DELETE",
  });

export const leaveGroup = (tripId, options = {}) =>
  apiRequest(`trips/${tripId}/leave/`, {
    ...options,
    method: "POST",
  });

export const listInvitations = (options = {}) =>
  apiRequest("trip-invitations/", options);

export const acceptInvitation = (id, options = {}) =>
  apiRequest(`trip-invitations/${id}/accept/`, {
    ...options,
    method: "POST",
  });

export const rejectInvitation = (id, options = {}) =>
  apiRequest(`trip-invitations/${id}/reject/`, {
    ...options,
    method: "POST",
  });

export const listPolls = (tripId, options = {}) =>
  apiRequest(`trips/${tripId}/polls/`, options);

export const getPoll = (tripId, id, options = {}) =>
  apiRequest(`trips/${tripId}/polls/${id}/`, options);

export const createPoll = (tripId, data, options = {}) =>
  apiRequest(`trips/${tripId}/polls/`, {
    ...options,
    method: "POST",
    data,
  });

export const voteInPoll = (tripId, id, optionId, options = {}) =>
  apiRequest(`trips/${tripId}/polls/${id}/vote/`, {
    ...options,
    method: "PUT",
    data: { option_id: optionId },
  });

export const closePoll = (tripId, id, data, options = {}) =>
  apiRequest(`trips/${tripId}/polls/${id}/close/`, {
    ...options,
    method: "POST",
    data,
  });

export function groupError(error) {
  return (
    Object.values(error.fields || {})
      .filter(Boolean)
      .join(" ") ||
    error.message ||
    "Não foi possível concluir. Tente novamente."
  );
}