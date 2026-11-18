// S2-01: somente endpoints do backend; não utiliza serviços de IA.
import { apiRequest } from "./trips";

export function searchPeople(search, options = {}) {
  return apiRequest(
    `users/?search=${encodeURIComponent(search.trim())}`,
    options,
  );
}

export function listFriends(options = {}) {
  return apiRequest("friends/", options);
}

export function listFriendRequests(options = {}) {
  return apiRequest("friend-requests/", options);
}

export function sendFriendRequest(recipientId, options = {}) {
  return apiRequest("friend-requests/", {
    ...options,
    method: "POST",
    data: { recipient_id: recipientId },
  });
}

export function acceptFriendRequest(requestId, options = {}) {
  return apiRequest(`friend-requests/${requestId}/accept/`, {
    ...options,
    method: "POST",
  });
}

export function rejectFriendRequest(requestId, options = {}) {
  return apiRequest(`friend-requests/${requestId}/reject/`, {
    ...options,
    method: "POST",
  });
}

export function cancelFriendRequest(requestId, options = {}) {
  return apiRequest(`friend-requests/${requestId}/`, {
    ...options,
    method: "DELETE",
  });
}

export function removeFriend(userId, options = {}) {
  return apiRequest(`friends/${userId}/`, {
    ...options,
    method: "DELETE",
  });
}