import re
import unicodedata
from decimal import Decimal

from rest_framework import serializers

from accounts.models import User

from .models import TripQuestionnaire


def normalized(value):
    text = unicodedata.normalize("NFKD", value.casefold())

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return " ".join(
        "".join(
            character if character.isalnum() else " "
            for character in text
        ).split()
    )


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if (
            not isinstance(data, dict)
            or set(data) - set(self.fields)
        ):
            raise serializers.ValidationError({
                "non_field_errors": [
                    "Objeto ou campos inválidos."
                ],
            })

        for key, value in data.items():
            field = self.fields[key]

            if (
                isinstance(field, serializers.CharField)
                and type(value) is not str
            ):
                raise serializers.ValidationError({
                    key: "Envie texto.",
                })

            if (
                isinstance(field, serializers.BooleanField)
                and type(value) is not bool
            ):
                raise serializers.ValidationError({
                    key: "Envie true ou false.",
                })

            if isinstance(field, serializers.DecimalField):
                if (
                    type(value) not in (int, float)
                    or not 0 < value <= 9_999_999_999.99
                ):
                    raise serializers.ValidationError({
                        key: "Envie um número finito.",
                    })

            if isinstance(field, serializers.ListField):
                if (
                    type(value) is not list
                    or any(
                        type(item) is not str
                        for item in value
                    )
                ):
                    raise serializers.ValidationError({
                        key: "Envie uma lista de textos.",
                    })

        return super().to_internal_value(data)


class RecommendationRequestSerializer(StrictSerializer):
    origin_country_code = serializers.RegexField(
        r"^[A-Z]{2}$"
    )

    refresh = serializers.BooleanField(default=False)


class DestinationCandidateSerializer(StrictSerializer):
    city = serializers.CharField(max_length=120)
    country = serializers.CharField(max_length=80)

    country_code = serializers.RegexField(
        r"^[A-Z]{2}$"
    )

    currency = serializers.RegexField(
        r"^[A-Z]{3}$"
    )

    cost_min = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    cost_max = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    landscape = serializers.ChoiceField(
        choices=[
            value
            for value, _ in TripQuestionnaire.Landscape.choices
            if value != "any"
        ],
    )

    climate = serializers.ChoiceField(
        choices=["warm", "mild", "cold"],
    )

    pace = serializers.ChoiceField(
        choices=["relaxed", "moderate", "intense"],
    )

    accommodation = serializers.ChoiceField(
        choices=[
            "hostel",
            "hotel",
            "apartment",
            "resort",
        ],
    )

    interests = serializers.ListField(
        child=serializers.ChoiceField(
            choices=User.Interest.choices,
        ),
        min_length=1,
        max_length=8,
    )

    reason = serializers.CharField(max_length=450)
    caveat = serializers.CharField(max_length=300)

    def validate(self, attrs):
        if attrs["cost_min"] > attrs["cost_max"]:
            raise serializers.ValidationError(
                "Faixa de custos invertida."
            )

        if len(attrs["interests"]) != len(
            set(attrs["interests"])
        ):
            raise serializers.ValidationError(
                "Interesses repetidos."
            )

        if not re.search(
            r"[^\W\d_]",
            attrs["city"],
            re.UNICODE,
        ):
            raise serializers.ValidationError(
                "Cidade inválida."
            )

        return attrs