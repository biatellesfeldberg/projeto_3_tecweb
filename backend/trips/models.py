from django.db import models

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator


class Trip(models.Model):
    """Uma viagem planejada por um usuário (tela 02 - Planejar viagem)."""

    class Mode(models.TextChoices):
        SOLO = "solo", "Por conta própria"
        GROUP = "group", "Com amigos"

    class Status(models.TextChoices):
        PLANNING = "planning", "Em planejamento"
        UPCOMING = "upcoming", "Próxima"
        COMPLETED = "completed", "Realizada"

    class Style(models.TextChoices):
        ECONOMIC = "economic", "Econômico"
        INTERMEDIATE = "intermediate", "Intermediário"
        COMFORT = "comfort", "Conforto"

    class Pace(models.TextChoices):
        RELAXED = "relaxed", "Tranquilo"
        MODERATE = "moderate", "Moderado"
        INTENSE = "intense", "Intenso"

    class Transport(models.TextChoices):
        PLANE = "plane", "Avião"
        CAR = "car", "Carro"
        BUS = "bus", "Ônibus"
        TRAIN = "train", "Trem"
        OTHER = "other", "Outro"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name="organizador",
    )
    title = models.CharField("título", max_length=120)
    description = models.TextField("descrição", blank=True)

    origin = models.CharField("cidade de origem", max_length=120)
    # Pode ficar vazio: "Ainda não escolhi meu destino".
    destination = models.CharField("destino", max_length=120, blank=True)

    start_date = models.DateField("data de início")
    end_date = models.DateField("data de término")

    travelers_count = models.PositiveSmallIntegerField(
        "número de viajantes",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
    )
    budget = models.DecimalField(
        "orçamento total",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField("moeda", max_length=3, default="BRL")

    mode = models.CharField(
        "tipo de viagem", max_length=10, choices=Mode.choices, default=Mode.SOLO
    )
    status = models.CharField(
        "status", max_length=10, choices=Status.choices, default=Status.PLANNING
    )

    # Preferências específicas desta viagem (podem vir do perfil e ser ajustadas).
    style = models.CharField(
        "estilo", max_length=15, choices=Style.choices, blank=True
    )
    pace = models.CharField("ritmo", max_length=10, choices=Pace.choices, blank=True)
    transport = models.CharField(
        "transporte", max_length=10, choices=Transport.choices, blank=True
    )
    interests = models.JSONField(
        "interesses",
        default=list,
        blank=True,
        help_text='Lista de interesses, ex.: ["gastronomia", "cultura"].',
    )

    cover_image_url = models.URLField("imagem de capa", blank=True)

    # Preenchidos pela geração de roteiro com IA (trips/itinerary.py).
    ai_summary = models.TextField("resumo do roteiro", blank=True)
    lodging_suggestions = models.JSONField(
        "sugestões de hospedagem", default=list, blank=True
    )
    cost_estimate = models.JSONField(
        "estimativa de custos", default=dict, blank=True
    )
    itinerary_generated_at = models.DateTimeField(
        "roteiro gerado em", null=True, blank=True
    )

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["start_date", "id"]
        verbose_name = "viagem"
        verbose_name_plural = "viagens"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="trip_end_date_after_start_date",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "A data de término deve ser igual ou posterior à data de início."}
            )

    @property
    def duration_days(self):
        """Quantidade de dias da viagem, contando o primeiro e o último."""
        if not (self.start_date and self.end_date):
            return 0
        return (self.end_date - self.start_date).days + 1


class TripDay(models.Model):
    """Um dia do roteiro de uma viagem (tela 03 - Roteiro da viagem)."""

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="days",
        verbose_name="viagem",
    )
    date = models.DateField("data")
    day_number = models.PositiveSmallIntegerField(
        "número do dia", validators=[MinValueValidator(1)]
    )
    title = models.CharField("título do dia", max_length=120, blank=True)
    notes = models.TextField("notas do dia", blank=True)

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["trip", "date"]
        verbose_name = "dia do roteiro"
        verbose_name_plural = "dias do roteiro"
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "date"], name="unique_trip_day_date"
            ),
            models.UniqueConstraint(
                fields=["trip", "day_number"], name="unique_trip_day_number"
            ),
        ]

    def __str__(self):
        return f"{self.trip} - dia {self.day_number} ({self.date:%d/%m/%Y})"

    def clean(self):
        super().clean()
        trip = getattr(self, "trip", None)
        if trip and self.date and trip.start_date and trip.end_date:
            if not (trip.start_date <= self.date <= trip.end_date):
                raise ValidationError(
                    {"date": "A data do dia precisa estar dentro do período da viagem."}
                )


class Activity(models.Model):
    """Uma atividade dentro de um dia do roteiro."""

    class Category(models.TextChoices):
        GASTRONOMY = "gastronomy", "Gastronomia"
        CULTURE = "culture", "Cultura"
        NATURE = "nature", "Natureza"
        BEACH = "beach", "Praia"
        SIGHTSEEING = "sightseeing", "Paisagem"
        SHOPPING = "shopping", "Compras"
        NIGHTLIFE = "nightlife", "Vida noturna"
        ADVENTURE = "adventure", "Aventura"
        TRANSPORT = "transport", "Deslocamento"
        LODGING = "lodging", "Hospedagem"
        FREE_TIME = "free_time", "Tempo livre"
        OTHER = "other", "Outro"

    class CostType(models.TextChoices):
        PER_PERSON = "per_person", "Por pessoa"
        TOTAL = "total", "Total do grupo"

    day = models.ForeignKey(
        TripDay,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="dia",
    )
    title = models.CharField("título", max_length=150)
    description = models.TextField("descrição", blank=True)
    category = models.CharField(
        "categoria", max_length=15, choices=Category.choices, default=Category.OTHER
    )

    # Horários e duração
    start_time = models.TimeField("horário de início", null=True, blank=True)
    end_time = models.TimeField("horário de término", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        "duração (minutos)", null=True, blank=True
    )

    # Localização (usada no mapa do dia)
    location_name = models.CharField("local", max_length=150, blank=True)
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

    # Custos
    estimated_cost = models.DecimalField(
        "custo estimado",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    cost_type = models.CharField(
        "tipo de custo",
        max_length=10,
        choices=CostType.choices,
        default=CostType.PER_PERSON,
    )

    notes = models.TextField("observações", blank=True)
    image_url = models.URLField("imagem", blank=True)
    order = models.PositiveSmallIntegerField("ordem", default=0)

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["day", "order", "start_time", "id"]
        verbose_name = "atividade"
        verbose_name_plural = "atividades"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(end_time__isnull=True)
                    | models.Q(start_time__isnull=True)
                    | models.Q(end_time__gte=models.F("start_time"))
                ),
                name="activity_end_time_after_start_time",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValidationError(
                {"end_time": "O horário de término deve ser posterior ao de início."}
            )

    @property
    def total_cost(self):
        """Custo total da atividade considerando o número de viajantes."""
        if self.cost_type == self.CostType.PER_PERSON:
            return self.estimated_cost * self.day.trip.travelers_count
        return self.estimated_cost
