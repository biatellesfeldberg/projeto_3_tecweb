from django.conf import settings
from django.db import models
from django.db.models.functions import Greatest, Least


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