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
            "days",
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


class ReorderSerializer(serializers.Serializer):
    activity_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
    )
