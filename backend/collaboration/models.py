from django.conf import settings
from django.db import models
from django.db.models.functions import Greatest, Least

from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACCEPTED = "accepted", "Aceita"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friendships",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friendships",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    sender=models.F("recipient"),
                ),
                name="friendship_no_self",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "accepted"],
                ),
                name="friendship_valid_status",
            ),
            models.UniqueConstraint(
                Least("sender", "recipient"),
                Greatest("sender", "recipient"),
                name="friendship_unique_pair",
            ),
        ]

    def __str__(self):
        return (
            f"{self.sender_id} / "
            f"{self.recipient_id}: {self.status}"
        )


class TripMembership(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Convite pendente"
        ACCEPTED = "accepted", "Participante"

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trip_memberships",
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_trip_invitations",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["trip", "user"],
                name="unique_trip_membership",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "accepted"],
                ),
                name="trip_membership_valid_status",
            ),
        ]

    def __str__(self):
        return (
            f"Viagem {self.trip_id} / "
            f"usuário {self.user_id}: {self.status}"
        )


class TripQuestionnaire(models.Model):
    class Landscape(models.TextChoices):
        BEACH = "beach", "Praia"
        MOUNTAIN = "mountain", "Montanha"
        CITY = "city", "Cidade"
        NATURE = "nature", "Natureza"
        ANY = "any", "Sem preferência"

    class Climate(models.TextChoices):
        WARM = "warm", "Quente"
        MILD = "mild", "Ameno"
        COLD = "cold", "Frio"
        ANY = "any", "Sem preferência"

    class Accommodation(models.TextChoices):
        HOSTEL = "hostel", "Hostel"
        HOTEL = "hotel", "Hotel"
        APARTMENT = "apartment", "Apartamento"
        RESORT = "resort", "Resort"
        ANY = "any", "Sem preferência"

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="questionnaire_answers",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trip_questionnaires",
    )

    currency = models.CharField(
        max_length=3,
        default="BRL",
    )

    landscape = models.CharField(
        max_length=10,
        choices=Landscape.choices,
    )

    max_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    days = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(60),
        ],
    )

    pace = models.CharField(
        max_length=10,
        choices=[
            ("relaxed", "Tranquilo"),
            ("moderate", "Moderado"),
            ("intense", "Intenso"),
        ],
    )

    gastronomy_importance = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    destination_preference = models.CharField(
        max_length=15,
        choices=[
            ("any", "Sem preferência"),
            ("domestic", "Nacionais"),
            ("international", "Internacionais"),
        ],
    )

    climate = models.CharField(
        max_length=10,
        choices=Climate.choices,
    )

    accommodation = models.CharField(
        max_length=12,
        choices=Accommodation.choices,
    )

    interests = models.JSONField(default=list)

    avoided_destinations = models.JSONField(
        default=list,
        blank=True,
    )

    notes = models.CharField(
        max_length=500,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "user"],
                name="unique_trip_questionnaire",
            ),
        ]

    def __str__(self):
        return (
            f"Questionário da viagem {self.trip_id} / "
            f"usuário {self.user_id}"
        )


class TripPoll(models.Model):
    class Category(models.TextChoices):
        DESTINATION = "destination", "Destino"
        RESTAURANT = "restaurant", "Restaurante"
        ACTIVITY = "activity", "Atividade"

    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Encerrada"

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        related_name="polls",
    )
    title = models.CharField(max_length=150)
    category = models.CharField(
        max_length=15,
        choices=Category.choices,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    decision = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["open", "closed"]),
                name="poll_valid_status",
            ),
        ]


class PollOption(models.Model):
    poll = models.ForeignKey(
        TripPoll,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=150)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "label"],
                name="unique_poll_option",
            ),
        ]


class PollVote(models.Model):
    poll = models.ForeignKey(
        TripPoll,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poll_votes",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"],
                name="unique_vote_per_poll_user",
            ),
        ]