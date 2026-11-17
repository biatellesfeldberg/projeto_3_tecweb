from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Friendship


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