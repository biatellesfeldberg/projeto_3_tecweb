from django.urls import path

from . import views


urlpatterns = [
    path(
        "places/",
        views.place_list,
        name="place-list",
    ),
    path(
        "places/<int:place_id>/",
        views.place_detail,
        name="place-detail",
    ),
    path(
        "trips/<int:trip_id>/places/",
        views.trip_place_list,
        name="trip-place-list",
    ),
    path(
        "trips/<int:trip_id>/places/<int:place_id>/",
        views.trip_place_detail,
        name="trip-place-detail",
    ),
]
