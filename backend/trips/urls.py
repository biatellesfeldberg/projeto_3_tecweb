from django.urls import path

from . import views


urlpatterns = [
    path(
        "trips/",
        views.trip_list,
        name="trip-list",
    ),
    path(
        "trips/<int:trip_id>/",
        views.trip_detail,
        name="trip-detail",
    ),
    path(
        "trips/<int:trip_id>/duplicate/",
        views.trip_duplicate,
        name="trip-duplicate",
    ),
    path(
        "trips/<int:trip_id>/generate-itinerary/",
        views.trip_generate_itinerary,
        name="trip-generate-itinerary",
    ),
    path(
        "trips/<int:trip_id>/destination-suggestions/",
        views.trip_destination_suggestions,
        name="trip-destination-suggestions",
    ),
    path(
        "trips/<int:trip_id>/days/<int:day_id>/",
        views.day_detail,
        name="trip-day-detail",
    ),
    path(
        "trips/<int:trip_id>/days/<int:day_id>/reorder/",
        views.day_reorder,
        name="trip-day-reorder",
    ),
    path(
        "trips/<int:trip_id>/activities/",
        views.activity_list,
        name="trip-activity-list",
    ),
    path(
        "trips/<int:trip_id>/activities/<int:activity_id>/",
        views.activity_detail,
        name="trip-activity-detail",
    ),
]
