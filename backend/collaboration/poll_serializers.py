from rest_framework import serializers

from .models import TripPoll


class StrictFieldsSerializer(serializers.Serializer):
    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)

        if unknown:
            raise serializers.ValidationError({
                field: ["Campo não permitido."]
                for field in sorted(unknown)
            })

        return attrs


class CreatePollSerializer(StrictFieldsSerializer):
    title = serializers.CharField(max_length=150)

    category = serializers.ChoiceField(
        choices=TripPoll.Category.choices,
    )

    options = serializers.ListField(
        child=serializers.CharField(max_length=150),
        min_length=2,
        max_length=10,
    )

    def validate_options(self, value):
        normalized = [label.casefold() for label in value]

        if len(normalized) != len(set(normalized)):
            raise serializers.ValidationError(
                "As opções não podem se repetir."
            )

        return value


class VoteSerializer(StrictFieldsSerializer):
    option_id = serializers.IntegerField(min_value=1)


class ClosePollSerializer(StrictFieldsSerializer):
    option_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)