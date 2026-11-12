from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from trips.models import Activity, Trip


class SavedPlace(models.Model):
    """Um lugar guardado pelo usuário (tela 04 - Meus lugares).

    Funciona como uma lista de desejos: o lugar existe independentemente de
    uma viagem e pode ser vinculado a uma ou mais viagens como sugestão.
    """

    # Mesmas chaves das atividades do roteiro, para que um lugar salvo possa
    # virar atividade sem conversão.
    Category = Activity.Category

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_places",
        verbose_name="dono",
    )
    name = models.CharField("nome", max_length=150)
    city = models.CharField("cidade", max_length=120, blank=True)
    country = models.CharField("país", max_length=120, blank=True)
    category = models.CharField(
        "categoria",
        max_length=15,
        choices=Category.choices,
        default=Category.OTHER,
    )
    description = models.TextField("descrição", blank=True)
    notes = models.TextField("observações", blank=True)

    # Localização (usada no mapa)
    address = models.CharField("endereço", max_length=255, blank=True)
    latitude = models.DecimalField(
        "latitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        "longitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    image_url = models.URLField("imagem", blank=True)

    trips = models.ManyToManyField(
        Trip,
        through="TripPlace",
        related_name="saved_places",
        blank=True,
        verbose_name="viagens",
    )

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "lugar salvo"
        verbose_name_plural = "lugares salvos"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name="saved_place_both_coordinates_or_none",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                "Informe a latitude e a longitude juntas, ou deixe as duas vazias."
            )


class TripPlace(models.Model):
    """Vínculo entre um lugar salvo e uma viagem (aba Lugares da viagem)."""

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="trip_places",
        verbose_name="viagem",
    )
    place = models.ForeignKey(
        SavedPlace,
        on_delete=models.CASCADE,
        related_name="trip_places",
        verbose_name="lugar",
    )
    added_at = models.DateTimeField("adicionado em", auto_now_add=True)

    class Meta:
        ordering = ["added_at", "id"]
        verbose_name = "lugar da viagem"
        verbose_name_plural = "lugares da viagem"
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "place"], name="unique_trip_place"
            ),
        ]

    def __str__(self):
        return f"{self.place} em {self.trip}"
