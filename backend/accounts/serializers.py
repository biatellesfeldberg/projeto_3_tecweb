from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=150)

    email = serializers.EmailField(
        max_length=254,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Já existe uma conta com este e-mail.",
            )
        ],
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "password_confirm",
        ]

    def validate_email(self, value):
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": [
                    "As senhas não coincidem."
                ],
            })

        user = User(
            first_name=attrs["first_name"],
            last_name=attrs.get("last_name", ""),
            email=attrs["email"],
        )

        try:
            validate_password(
                attrs["password"],
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": error.messages,
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        try:
            with transaction.atomic():
                return User.objects.create_user(
                    username=uuid4().hex,
                    **validated_data,
                )
        except IntegrityError:
            raise serializers.ValidationError({
                "email": [
                    "Não foi possível cadastrar este e-mail. "
                    "Verifique se já existe uma conta."
                ],
            })


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

class ProfileSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "bio",
            "home_city",
            "photo",
            "preferred_destinations",
            "interests",
            "style",
            "pace",
            "destination_preference",
        ]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=False,
    )

    preferred_destinations = serializers.ListField(
        child=serializers.CharField(max_length=120),
        max_length=20,
        required=False,
    )

    interests = serializers.ListField(
        child=serializers.ChoiceField(
            choices=User.Interest.choices,
        ),
        max_length=20,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "bio",
            "home_city",
            "preferred_destinations",
            "interests",
            "style",
            "pace",
            "destination_preference",
        ]

    def validate(self, attrs):
        unknown_fields = set(self.initial_data) - set(self.fields)

        if unknown_fields:
            raise serializers.ValidationError({
                field: ["Campo não permitido nesta atualização."]
                for field in sorted(unknown_fields)
            })

        return attrs

    def validate_preferred_destinations(self, value):
        return list(dict.fromkeys(value))

    def validate_interests(self, value):
        return list(dict.fromkeys(value))


class ProfilePhotoSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=True)

    class Meta:
        model = User
        fields = ["photo"]

    def validate_photo(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "A foto deve ter no máximo 5 MB."
            )

        if value.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError(
                "Envie uma imagem JPEG, PNG ou WebP."
            )

        return value