from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class TravelStyle(models.TextChoices):
        ECONOMIC = "economic", "Econômico"
        INTERMEDIATE = "intermediate", "Intermediário"
        COMFORT = "comfort", "Conforto / luxuoso"

    class TravelPace(models.TextChoices):
        RELAXED = "relaxed", "Tranquilo"
        MODERATE = "moderate", "Moderado"
        INTENSE = "intense", "Intenso"

    class DestinationPreference(models.TextChoices):
        ANY = "any", "Sem preferência"
        DOMESTIC = "domestic", "Nacionais"
        INTERNATIONAL = "international", "Internacionais"

    class Interest(models.TextChoices):
        BEACH = "beach", "Praia"
        NATURE = "nature", "Natureza"
        GASTRONOMY = "gastronomy", "Gastronomia"
        ADVENTURE = "adventure", "Aventura"
        CULTURE = "culture", "Cultura"
        SHOPPING = "shopping", "Compras"
        NIGHTLIFE = "nightlife", "Vida noturna"
        SIGHTSEEING = "sightseeing", "Paisagens"

    email = models.EmailField(unique=True)

    bio = models.CharField(
        max_length=500,
        blank=True,
    )

    home_city = models.CharField(
        max_length=120,
        blank=True,
    )

    photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True,
    )

    preferred_destinations = models.JSONField(
        default=list,
        blank=True,
    )

    interests = models.JSONField(
        default=list,
        blank=True,
    )

    style = models.CharField(
        max_length=15,
        choices=TravelStyle.choices,
        blank=True,
    )

    pace = models.CharField(
        max_length=10,
        choices=TravelPace.choices,
        blank=True,
    )

    destination_preference = models.CharField(
        max_length=15,
        choices=DestinationPreference.choices,
        default=DestinationPreference.ANY,
    )
