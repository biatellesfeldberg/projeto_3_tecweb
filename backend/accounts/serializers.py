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