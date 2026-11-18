"""S2-05: dados locais de demonstração, sem usar serviços externos."""

from datetime import timedelta
from itertools import combinations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from collaboration.models import (
    Friendship,
    PollOption,
    PollVote,
    TripMembership,
    TripPoll,
    TripQuestionnaire,
)
from collaboration.poll_views import poll_results

from trips.models import Trip
from trips.services import sync_days


User = get_user_model()

PASSWORD = "RumoDemo2026!"
MARKER = "[S2-05-DEMO]"

ACCOUNTS = {
    "ana": (
        "Ana",
        "intermediate",
        "moderate",
        ["culture", "gastronomy"],
    ),
    "bia": (
        "Bia",
        "intermediate",
        "moderate",
        ["culture", "gastronomy"],
    ),
    "luana": (
        "Luana",
        "intermediate",
        "moderate",
        ["culture", "sightseeing"],
    ),
    "renata": (
        "Renata",
        "economic",
        "moderate",
        ["nature", "adventure"],
    ),
    "pedro": (
        "Pedro",
        "comfort",
        "relaxed",
        ["beach", "gastronomy"],
    ),
    "clara": (
        "Clara",
        "economic",
        "intense",
        ["culture", "nightlife"],
    ),
    "nina": (
        "Nina",
        "economic",
        "relaxed",
        ["nature", "beach"],
    ),
}

ANSWER_BASE = {
    "landscape": "city",
    "max_budget": "4000.00",
    "days": 4,
    "pace": "moderate",
    "gastronomy_importance": 4,
    "destination_preference": "domestic",
    "climate": "mild",
    "accommodation": "hotel",
    "interests": ["culture", "gastronomy"],
    "avoided_destinations": [],
    "notes": "Resposta fictícia para demonstração.",
}


class Command(BaseCommand):
    help = (
        "Cria os cenários colaborativos da S2-05, "
        "sem chamar a IA."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Recria as viagens marcadas como demo "
                "e restaura as contas de exemplo."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self._check_accounts()

        users = self._accounts(
            reset=options["reset"],
        )

        user_ids = [
            user.pk
            for user in users.values()
        ]

        if options["reset"]:
            # Remove somente viagens marcadas como demonstração
            # e pertencentes às contas reservadas.
            Trip.objects.filter(
                owner_id__in=user_ids,
                description__startswith=MARKER,
            ).delete()

            # Preserva amizades com contas externas à demonstração.
            Friendship.objects.filter(
                sender_id__in=user_ids,
                recipient_id__in=user_ids,
            ).delete()

        # As quatro pessoas principais são amigas entre si.
        for first, second in combinations(
            ("ana", "bia", "luana", "renata"),
            2,
        ):
            self._friendship(
                users[first],
                users[second],
                "accepted",
            )

        # Uma solicitação recebida e outra enviada pela Ana.
        self._friendship(
            users["pedro"],
            users["ana"],
            "pending",
        )

        self._friendship(
            users["ana"],
            users["clara"],
            "pending",
        )

        start = timezone.localdate() + timedelta(days=30)

        compatible = self._trip(
            users["ana"],
            "Preferências compatíveis",
            start,
            4,
            "12000.00",
            (
                "Todos gostam de cidade, cultura e gastronomia, "
                "com ritmo moderado."
            ),
        )

        conflicting = self._trip(
            users["bia"],
            "Preferências conflitantes",
            start + timedelta(days=30),
            7,
            "18000.00",
            (
                "Orçamento, duração, paisagem e clima divergem."
            ),
        )

        incomplete = self._trip(
            users["renata"],
            "Questionário incompleto",
            start + timedelta(days=60),
            4,
            "9000.00",
            (
                "Só a organizadora respondeu; "
                "duas participantes ainda não."
            ),
        )

        # A organizadora já pertence à viagem pelo campo owner.
        # Não criamos uma participação duplicada para ela.
        for trip, accepted, pending in (
            (
                compatible,
                ("bia", "luana"),
                "renata",
            ),
            (
                conflicting,
                ("ana", "renata"),
                "luana",
            ),
            (
                incomplete,
                ("ana", "luana"),
                "bia",
            ),
        ):
            for name in accepted:
                self._membership(
                    trip,
                    users[name],
                    "accepted",
                )

            self._membership(
                trip,
                users[pending],
                "pending",
            )

        # Cenário 1: preferências semelhantes.
        for name, budget in (
            ("ana", "4000.00"),
            ("bia", "4500.00"),
            ("luana", "4200.00"),
        ):
            self._answer(
                compatible,
                users[name],
                max_budget=budget,
            )

        # Cenário 2: preferências conflitantes.
        self._answer(
            conflicting,
            users["ana"],
            landscape="beach",
            max_budget="2500.00",
            days=7,
            pace="relaxed",
            gastronomy_importance=5,
            climate="warm",
            accommodation="resort",
            interests=["beach", "gastronomy"],
            avoided_destinations=["Gramado"],
            notes=(
                "Prefere praia quente e descanso no Brasil."
            ),
        )

        self._answer(
            conflicting,
            users["bia"],
            max_budget="12000.00",
            days=10,
            pace="intense",
            gastronomy_importance=3,
            destination_preference="international",
            climate="cold",
            interests=[
                "culture",
                "shopping",
                "nightlife",
            ],
            avoided_destinations=["Fortaleza"],
            notes=(
                "Prefere cidade fria e viagem internacional."
            ),
        )

        self._answer(
            conflicting,
            users["renata"],
            landscape="mountain",
            max_budget="1500.00",
            days=3,
            gastronomy_importance=1,
            climate="cold",
            accommodation="hostel",
            interests=["nature", "adventure"],
            avoided_destinations=["Lisboa"],
            notes=(
                "Prefere montanha, viagem curta "
                "e econômica no Brasil."
            ),
        )

        # Cenário 3: só a organizadora respondeu.
        self._answer(
            incomplete,
            users["renata"],
            max_budget="3000.00",
        )

        # Aberta: Luana ainda pode votar.
        self._poll(
            compatible,
            "Qual será o destino?",
            "destination",
            (
                "Curitiba",
                "Belo Horizonte",
                "São Paulo",
            ),
            {
                users["ana"]: 0,
                users["bia"]: 0,
            },
        )

        # Encerrada: museu vence por dois votos a um.
        self._poll(
            compatible,
            "Qual passeio será a prioridade?",
            "activity",
            (
                "Visita ao museu",
                "Caminhada no centro histórico",
            ),
            {
                users["ana"]: 0,
                users["bia"]: 0,
                users["luana"]: 1,
            },
            closed=True,
        )

        # Aberta: empate entre as três opções.
        self._poll(
            conflicting,
            "Como conciliar o destino?",
            "destination",
            (
                "Fortaleza",
                "Lisboa",
                "Gramado",
            ),
            {
                users["ana"]: 0,
                users["bia"]: 1,
                users["renata"]: 2,
            },
        )

        # Aberta: nenhum voto.
        self._poll(
            incomplete,
            "Qual restaurante vamos escolher?",
            "restaurant",
            (
                "Restaurante Demo Centro",
                "Restaurante Demo Verde",
            ),
            {},
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Dados colaborativos de demonstração preparados."
            )
        )

        self.stdout.write(
            "Senha inicial "
            f"(contas novas ou --reset): {PASSWORD}"
        )

        for user in users.values():
            self.stdout.write(
                f"Conta {user.pk}: {user.email}"
            )

        for trip in (
            compatible,
            conflicting,
            incomplete,
        ):
            self.stdout.write(
                f"Viagem {trip.pk}: {trip.title} "
                f"| organizadora: {trip.owner.email}"
            )

        self.stdout.write(
            "Sem --reset, registros existentes "
            "e suas alterações são preservados."
        )

    def _check_accounts(self):
        for name in ACCOUNTS:
            username = f"rumo_demo_{name}"
            email = f"{name}.demo@example.com"

            matches = User.objects.filter(
                Q(username=username)
                | Q(email__iexact=email)
            )

            for user in matches:
                if (
                    user.username != username
                    or user.email.lower() != email
                    or user.is_staff
                    or user.is_superuser
                ):
                    raise CommandError(
                        "Colisão com a conta reservada "
                        f"{email}. Nenhum dado foi alterado."
                    )

    def _accounts(self, reset):
        users = {}

        for name, (
            first_name,
            style,
            pace,
            interests,
        ) in ACCOUNTS.items():
            defaults = {
                "email": f"{name}.demo@example.com",
                "first_name": first_name,
                "last_name": "Demo",
                "home_city": "São Paulo",
                "style": style,
                "pace": pace,
                "interests": interests,
                "destination_preference": "domestic",
                "bio": (
                    f"{MARKER} Conta fictícia "
                    "para testes e apresentação."
                ),
            }

            user, created = User.objects.get_or_create(
                username=f"rumo_demo_{name}",
                defaults=defaults,
            )

            if created or reset:
                for field, value in defaults.items():
                    setattr(user, field, value)

                user.is_active = True
                user.set_password(PASSWORD)
                user.full_clean()
                user.save()

            users[name] = user

        return users

    def _friendship(self, sender, recipient, status):
        exists = Friendship.objects.filter(
            Q(
                sender=sender,
                recipient=recipient,
            )
            | Q(
                sender=recipient,
                recipient=sender,
            ),
        ).exists()

        if not exists:
            link = Friendship(
                sender=sender,
                recipient=recipient,
                status=status,
            )

            link.full_clean()
            link.save()

    def _trip(
        self,
        owner,
        title,
        start,
        days,
        budget,
        description,
    ):
        title = f"[DEMO] {title}"

        existing = Trip.objects.filter(
            owner=owner,
            title=title,
        )

        if (
            existing.exclude(
                description__startswith=MARKER,
            ).exists()
            or existing.count() > 1
        ):
            raise CommandError(
                f"Colisão com a viagem {title}. "
                "Nenhum dado foi alterado."
            )

        trip, created = Trip.objects.get_or_create(
            owner=owner,
            title=title,
            defaults={
                "description": f"{MARKER} {description}",
                "origin": "São Paulo",
                "destination": "",
                "start_date": start,
                "end_date": (
                    start + timedelta(days=days - 1)
                ),
                "travelers_count": 3,
                "budget": budget,
                "currency": "BRL",
                "mode": "group",
                "status": "planning",
                "style": "intermediate",
                "pace": "moderate",
                "transport": "plane",
                "interests": [
                    "culture",
                    "gastronomy",
                ],
            },
        )

        if created:
            trip.full_clean(
                exclude=[
                    "lodging_suggestions",
                    "cost_estimate",
                ],
            )
            sync_days(trip)

        return trip

    def _membership(self, trip, user, status):
        member, created = TripMembership.objects.get_or_create(
            trip=trip,
            user=user,
            defaults={
                "invited_by": trip.owner,
                "status": status,
            },
        )

        if created:
            member.full_clean()

    def _answer(self, trip, user, **overrides):
        answer, created = TripQuestionnaire.objects.get_or_create(
            trip=trip,
            user=user,
            defaults={
                **ANSWER_BASE,
                "currency": trip.currency,
                **overrides,
            },
        )

        if created:
            answer.full_clean()

    def _poll(
        self,
        trip,
        title,
        category,
        labels,
        votes,
        closed=False,
    ):
        poll, created = TripPoll.objects.get_or_create(
            trip=trip,
            title=title,
            defaults={
                "category": category,
            },
        )

        if not created:
            return

        poll.full_clean()

        options = []

        for label in labels:
            option = PollOption.objects.create(
                poll=poll,
                label=label,
            )

            option.full_clean()
            options.append(option)

        for user, index in votes.items():
            vote = PollVote.objects.create(
                poll=poll,
                user=user,
                option=options[index],
            )

            vote.full_clean()

        if closed:
            results = poll_results(poll)

            chosen = max(
                results["options"],
                key=lambda item: item["votes"],
            )

            poll.status = TripPoll.Status.CLOSED
            poll.closed_at = timezone.now()

            poll.decision = {
                "option_id": chosen["id"],
                "label": chosen["label"],
                "reason": (
                    "Decisão de demonstração: "
                    "opção com mais votos."
                ),
                "decided_by": trip.owner_id,
                "results": results,
            }

            poll.full_clean()

            poll.save(
                update_fields=[
                    "status",
                    "closed_at",
                    "decision",
                ],
            )