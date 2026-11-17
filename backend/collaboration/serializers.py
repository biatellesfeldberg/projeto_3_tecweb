from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.db.models import Q

from .models import Friendship, TripMembership, TripQuestionnaire


User = get_user_model()


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
        ]


class FriendshipSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)
    recipient = PublicUserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = [
            "id",
            "sender",
            "recipient",
            "status",
            "created_at",
        ]


class SendFriendRequestSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(min_value=1)

    def validate_recipient_id(self, value):
        if value == self.context["request"].user.pk:
            raise serializers.ValidationError(
                "Você não pode adicionar a si mesma."
            )

        if not User.objects.filter(
            pk=value,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "Usuário não encontrado."
            )

        return value

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)

        if unknown:
            raise serializers.ValidationError({
                field: ["Campo não permitido."]
                for field in sorted(unknown)
            })

        return attrs


class TripMembershipSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    invited_by = PublicUserSerializer(read_only=True)

    trip_title = serializers.CharField(
        source="trip.title",
        read_only=True,
    )

    class Meta:
        model = TripMembership

        fields = [
            "id",
            "trip",
            "trip_title",
            "user",
            "invited_by",
            "status",
            "created_at",
        ]

        read_only_fields = fields


class InviteTripMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)

    def validate_user_id(self, value):
        trip = self.context["trip"]

        if value == trip.owner_id:
            raise serializers.ValidationError(
                "A organizadora já faz parte da viagem."
            )

        if not User.objects.filter(
            pk=value,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "Usuário não encontrado."
            )

        friends = Friendship.objects.filter(
            status=Friendship.Status.ACCEPTED,
        ).filter(
            Q(
                sender_id=trip.owner_id,
                recipient_id=value,
            )
            | Q(
                recipient_id=trip.owner_id,
                sender_id=value,
            )
        )

        if not friends.exists():
            raise serializers.ValidationError(
                "Convide apenas pessoas da sua lista de amigas."
            )

        return value

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)

        if unknown:
            raise serializers.ValidationError({
                field: ["Campo não permitido."]
                for field in sorted(unknown)
            })

        return attrs


class TripQuestionnaireSerializer(serializers.ModelSerializer):
    interests = serializers.ListField(
        child=serializers.ChoiceField(
            choices=User.Interest.choices,
        ),
        required=True,
        allow_empty=False,
        max_length=20,
    )

    avoided_destinations = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        default=list,
        max_length=20,
    )

    notes = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default="",
    )

    class Meta:
        model = TripQuestionnaire

        fields = [
            "id",
            "trip",
            "user",
            "currency",
            "landscape",
            "max_budget",
            "days",
            "pace",
            "gastronomy_importance",
            "destination_preference",
            "climate",
            "accommodation",
            "interests",
            "avoided_destinations",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "trip",
            "user",
            "currency",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        writable = (
            set(self.fields)
            - set(self.Meta.read_only_fields)
        )

        invalid_fields = set(self.initial_data) - writable

        if invalid_fields:
            raise serializers.ValidationError({
                field: ["Campo não permitido."]
                for field in sorted(invalid_fields)
            })

        return attrs

    def validate_interests(self, value):
        return list(dict.fromkeys(value))

    def validate_avoided_destinations(self, value):
        return list(dict.fromkeys(value))