from django.urls import path

from . import views


urlpatterns = [
    path(
        "users/",
        views.user_search,
        name="user-search",
    ),
    path(
        "friends/",
        views.friend_list,
        name="friend-list",
    ),
    path(
        "friends/<int:user_id>/",
        views.remove_friend,
        name="friend-remove",
    ),
    path(
        "friend-requests/",
        views.friend_request_list,
        name="friend-request-list",
    ),
    path(
        "friend-requests/<int:request_id>/",
        views.cancel_friend_request,
        name="friend-request-cancel",
    ),
    path(
        "friend-requests/<int:request_id>/accept/",
        views.accept_friend_request,
        name="friend-request-accept",
    ),
    path(
        "friend-requests/<int:request_id>/reject/",
        views.reject_friend_request,
        name="friend-request-reject",
    ),
]