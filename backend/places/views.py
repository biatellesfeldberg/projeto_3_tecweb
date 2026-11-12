from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SavedPlace, TripPlace
from .permissions import trips_for_user
from .serializers import PlaceSerializer, TripPlacesSerializer


def _get_or_404(queryset, **lookup):
    # Resposta padrão do contrato ({"detail": "Não encontrado."}), sem revelar
    # se o objeto existe e pertence a outra pessoa.
    obj = queryset.filter(**lookup).first()
    if obj is None:
        raise NotFound()
    return obj


def _user_places(user):
    return SavedPlace.objects.filter(owner=user).prefetch_related("trips")


def _filter_places(queryset, params):
    search = params.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(city__icontains=search)
            | Q(country__icontains=search)
            | Q(address__icontains=search)
            | Q(description__icontains=search)
            | Q(notes__icontains=search)
        )

    category = params.get("category", "").strip()
    if category:
        if category not in SavedPlace.Category.values:
            raise ValidationError(
                {"category": [f'"{category}" não é uma escolha válida.']}
            )
        queryset = queryset.filter(category=category)

    city = params.get("city", "").strip()
    if city:
        queryset = queryset.filter(city__iexact=city)

    trip = params.get("trip", "").strip()
    if trip == "none":
        queryset = queryset.filter(trips__isnull=True)
    elif trip:
        if not trip.isdigit():
            raise ValidationError(
                {"trip": ['Use o id de uma viagem ou "none".']}
            )
        queryset = queryset.filter(trips__id=int(trip))

    return queryset.distinct()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def place_list(request):
    if request.method == "POST":
        serializer = PlaceSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        place = serializer.save(owner=request.user)

        return Response(
            PlaceSerializer(place, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    places = _filter_places(_user_places(request.user), request.query_params)

    return Response(
        PlaceSerializer(places, many=True, context={"request": request}).data
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def place_detail(request, place_id):
    # Lugar de outra pessoa responde 404, sem revelar que ele existe.
    place = _get_or_404(_user_places(request.user), id=place_id)

    if request.method == "DELETE":
        place.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PATCH":
        serializer = PlaceSerializer(
            place,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        place = serializer.save()

    return Response(PlaceSerializer(place, context={"request": request}).data)


def _trip_places_response(request, trip):
    links = (
        TripPlace.objects.filter(trip=trip, place__owner=request.user)
        .select_related("place")
        .prefetch_related("place__trips")
        .order_by("added_at", "id")
    )
    places = [link.place for link in links]
    return Response(
        PlaceSerializer(places, many=True, context={"request": request}).data
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def trip_place_list(request, trip_id):
    trip = _get_or_404(trips_for_user(request.user), id=trip_id)

    if request.method == "POST":
        serializer = TripPlacesSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        already_linked = set(
            TripPlace.objects.filter(trip=trip).values_list("place_id", flat=True)
        )
        TripPlace.objects.bulk_create(
            [
                TripPlace(trip=trip, place=place)
                for place in serializer.validated_data["place_ids"]
                if place.id not in already_linked
            ]
        )

    return _trip_places_response(request, trip)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def trip_place_detail(request, trip_id, place_id):
    trip = _get_or_404(trips_for_user(request.user), id=trip_id)
    link = _get_or_404(
        TripPlace.objects.all(),
        trip=trip,
        place_id=place_id,
        place__owner=request.user,
    )
    link.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)
