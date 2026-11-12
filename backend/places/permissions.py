from trips.models import Trip


def trips_for_user(user):
    """Viagens às quais o usuário pode vincular lugares.

    Na Sprint 1 são só as viagens que ele organiza. Quando os integrantes de
    viagem existirem (Sprint 2), basta incluir aqui as viagens em que ele
    participa.
    """
    return Trip.objects.filter(owner=user)
