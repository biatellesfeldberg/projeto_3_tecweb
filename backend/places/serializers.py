from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from rest_framework import serializers

from .models import SavedPlace
from .permissions import trips_for_user


class CoordinateField(serializers.DecimalField):
    """Coordenada com 6 casas decimais.

    Valores com mais casas (comuns em APIs de mapa) são arredondados em vez
    de recusados.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 9)
        kwargs.setdefault("decimal_places", 6)
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            data = str(
                Decimal(str(data).strip()).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )
            )
        except (InvalidOperation, ValueError):
            pass  # O DecimalField devolve a mensagem de valor inválido.
        return super().to_internal_value(data)


class PlaceTripSerializer(serializers.Serializer):
    """Resumo da viagem à qual o lugar está vinculado."""

    id = serializers.IntegerField()
    title = serializers.CharField()


class PlaceSerializer(serializers.ModelSerializer):
    latitude = CoordinateField(min_value=-90, max_value=90)
    longitude = CoordinateField(min_value=-180, max_value=180)

    trips = serializers.SerializerMethodField()
    trip_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        help_text="Viagens às quais o lugar fica vinculado (substitui as atuais).",
    )

    class Meta:
        model = SavedPlace
        fields = [
            "id",
            "name",
            "city",
            "country",
            "category",
            "description",
            "notes",
            "address",
            "latitude",
            "longitude",
            "image_url",
            "trips",
            "trip_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_trips(self, place):
        user = self.context["request"].user

        trips = [
            trip
            for trip in place.trips.all()
            if trip.owner_id == user.pk
        ]

        trips.sort(
            key=lambda trip: (
                trip.start_date,
                trip.id,
            )
        )

        return PlaceTripSerializer(
            trips,
            many=True,
        ).data

    def validate_trip_ids(self, value):
        trip_ids = list(dict.fromkeys(value))  # Remove repetidos, mantendo a ordem.
        user = self.context["request"].user
        trips = list(trips_for_user(user).filter(id__in=trip_ids))

        if len(trips) != len(trip_ids):
            raise serializers.ValidationError("Viagem não encontrada.")

        return trips

    def validate(self, attrs):
        attrs = super().validate(attrs)

        latitude = attrs.get(
            "latitude", getattr(self.instance, "latitude", None)
        )
        longitude = attrs.get(
            "longitude", getattr(self.instance, "longitude", None)
        )
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {
                    "latitude": [
                        "Informe a latitude e a longitude juntas, "
                        "ou deixe as duas vazias."
                    ]
                }
            )

        return attrs

    def create(self, validated_data):
        trips = validated_data.pop("trip_ids", None)
        place = SavedPlace.objects.create(**validated_data)
        if trips:
            place.trips.set(trips)
        return place

    def update(self, instance, validated_data):
        trips = validated_data.pop("trip_ids", None)
        instance = super().update(instance, validated_data)
        if trips is not None:
            instance.trips.set(trips)
        return instance


class TripPlacesSerializer(serializers.Serializer):
    """Corpo de POST /api/trips/{trip_id}/places/."""

    place_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_place_ids(self, value):
        place_ids = list(dict.fromkeys(value))
        user = self.context["request"].user
        places = SavedPlace.objects.filter(owner=user, id__in=place_ids).in_bulk()

        if len(places) != len(place_ids):
            raise serializers.ValidationError("Lugar não encontrado.")

        # Mantém a ordem enviada: é a ordem em que aparecem na viagem.
        return [places[place_id] for place_id in place_ids]
