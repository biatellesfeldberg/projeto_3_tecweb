from decimal import Decimal

from rest_framework import serializers

from accounts.models import User

from .models import Activity, Trip, TripDay


# Viagens muito longas criariam centenas de dias vazios.
MAX_TRIP_DAYS = 60


class ActivitySerializer(serializers.ModelSerializer):
    day = serializers.PrimaryKeyRelatedField(
        queryset=TripDay.objects.none(),
        error_messages={
            "does_not_exist": "Este dia não pertence a esta viagem.",
            "incorrect_type": "Este dia não pertence a esta viagem.",
        },
    )
    total_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Activity
        fields = [
            "id",
            "day",
            "title",
            "description",
            "category",
            "start_time",
            "end_time",
            "duration_minutes",
            "location_name",
            "address",
            "latitude",
            "longitude",
            "estimated_cost",
            "cost_type",
            "total_cost",
            "notes",
            "image_url",
            "order",
        ]
        extra_kwargs = {
            "order": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só os dias da própria viagem podem ser escolhidos. Um dia de outra
        # viagem (ou de outra pessoa) recebe a mesma mensagem de um dia
        # inexistente, sem revelar que ele existe.
        trip = self.context.get("trip")
        if trip is not None:
            self.fields["day"].queryset = TripDay.objects.filter(trip=trip)

    def validate(self, attrs):
        start_time = attrs.get(
            "start_time", getattr(self.instance, "start_time", None)
        )
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if start_time and end_time and end_time < start_time:
            raise serializers.ValidationError({
                "end_time": [
                    "O horário de término deve ser posterior ao de início."
                ],
            })

        return attrs


class TripDaySerializer(serializers.ModelSerializer):
    activities = ActivitySerializer(many=True, read_only=True)

    class Meta:
        model = TripDay
        fields = [
            "id",
            "date",
            "day_number",
            "title",
            "notes",
            "activities",
        ]
        read_only_fields = ["date", "day_number"]


class TripSummarySerializer(serializers.ModelSerializer):
    duration_days = serializers.IntegerField(read_only=True)
    owner_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "title",
            "origin",
            "destination",
            "start_date",
            "end_date",
            "duration_days",
            "travelers_count",
            "budget",
            "currency",
            "mode",
            "status",
            "cover_image_url",
            "created_at",
            "updated_at",
            "owner_id",
        ]


class TripDetailSerializer(TripSummarySerializer):
    days = TripDaySerializer(many=True, read_only=True)

    class Meta(TripSummarySerializer.Meta):
        fields = TripSummarySerializer.Meta.fields + [
            "description",
            "style",
            "pace",
            "transport",
            "interests",
            "ai_summary",
            "lodging_suggestions",
            "cost_estimate",
            "itinerary_generated_at",
            "days",
        ]
        read_only_fields = [
            "ai_summary",
            "lodging_suggestions",
            "cost_estimate",
            "itinerary_generated_at",
        ]


class TripWriteSerializer(serializers.ModelSerializer):
    """Valida os dados de criação e edição de uma viagem."""

    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=User.Interest.choices),
        max_length=20,
        required=False,
    )

    class Meta:
        model = Trip
        fields = [
            "title",
            "description",
            "origin",
            "destination",
            "start_date",
            "end_date",
            "travelers_count",
            "budget",
            "currency",
            "mode",
            "status",
            "style",
            "pace",
            "transport",
            "interests",
            "cover_image_url",
        ]

    def validate_interests(self, value):
        return list(dict.fromkeys(value))

    def validate(self, attrs):
        if (
            self.instance is not None
            and attrs.get("mode") == Trip.Mode.SOLO
            and self.instance.memberships.exists()
        ):
            raise serializers.ValidationError({
                "mode": [
                    "Remova os convites e participantes antes "
                    "de mudar para viagem individual."
                ],
            })
        
        start_date = attrs.get(
            "start_date", getattr(self.instance, "start_date", None)
        )
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    "end_date": [
                        "A data de término deve ser igual ou posterior à "
                        "data de início."
                    ],
                })

            if (end_date - start_date).days + 1 > MAX_TRIP_DAYS:
                raise serializers.ValidationError({
                    "end_date": [
                        f"A viagem pode ter no máximo {MAX_TRIP_DAYS} dias."
                    ],
                })

        return attrs


class TripDayUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripDay
        fields = ["title", "notes"]


class GenerateItinerarySerializer(serializers.Serializer):
    replace_existing = serializers.BooleanField(default=True)
    extra_instructions = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )


class DestinationSuggestionsSerializer(serializers.Serializer):
    extra_instructions = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )


class ReorderSerializer(serializers.Serializer):
    activity_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
    )


class CostCalculatorSerializer(serializers.Serializer):
    """
    Pedido da calculadora. Recebe a viagem no contexto para usar a duração
    e o orçamento dela quando os campos não forem enviados.
    """

    class Mode:
        DURATION = "duration"
        BUDGET = "budget"
        CHOICES = [
            (DURATION, "Custo estimado para uma duração"),
            (BUDGET, "Duração possível para um orçamento"),
        ]

    mode = serializers.ChoiceField(choices=Mode.CHOICES)
    days = serializers.IntegerField(
        min_value=1,
        max_value=MAX_TRIP_DAYS,
        required=False,
    )
    budget = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    style = serializers.ChoiceField(
        choices=Trip.Style.choices,
        required=False,
        allow_blank=True,
    )
    refresh = serializers.BooleanField(default=False)

    def validate(self, attrs):
        trip = self.context["trip"]

        if "style" not in attrs:
            attrs["style"] = trip.style

        if attrs["mode"] == self.Mode.DURATION:
            attrs.setdefault("days", trip.duration_days)
        elif "budget" not in attrs:
            if trip.budget is None or trip.budget <= 0:
                raise serializers.ValidationError({
                    "budget": [
                        "Informe um orçamento ou cadastre um na viagem."
                    ],
                })
            attrs["budget"] = trip.budget

        return attrs


MAX_PLACES_PER_PROPOSAL = 10


class ReplanSerializer(serializers.Serializer):
    """
    Pedido de ajuste do roteiro. Recebe no contexto a viagem e a pessoa que
    pede, para conferir os dias e os lugares enviados.
    """

    request = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )
    place_ids = serializers.ListField(
        child=serializers.IntegerField(),
        max_length=MAX_PLACES_PER_PROPOSAL,
        required=False,
        default=list,
    )
    day_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate_request(self, value):
        return value.strip()

    def validate_place_ids(self, value):
        from places.models import SavedPlace

        ids = list(dict.fromkeys(value))
        # Só os lugares da própria pessoa. Os de outra pessoa recebem a mesma
        # mensagem de um lugar inexistente.
        places = {
            place.id: place
            for place in SavedPlace.objects.filter(
                owner=self.context["user"],
                id__in=ids,
            )
        }
        if len(places) != len(ids):
            raise serializers.ValidationError("Lugar não encontrado.")
        return [places[place_id] for place_id in ids]

    def validate_day_ids(self, value):
        ids = list(dict.fromkeys(value))
        if not ids:
            return None
        days = list(self.context["trip"].days.filter(id__in=ids))
        if len(days) != len(ids):
            raise serializers.ValidationError("Este dia não pertence a esta viagem.")
        return days

    def validate(self, attrs):
        if not attrs["request"] and not attrs["place_ids"]:
            raise serializers.ValidationError({
                "request": [
                    "Descreva o que quer mudar ou escolha lugares para incluir."
                ],
            })
        return attrs
