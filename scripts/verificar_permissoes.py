"""Verifica, no site publicado, se uma conta não acessa os dados de outra.

Uso (na raiz do repositório, com qualquer Python 3):

    python scripts/verificar_permissoes.py
    python scripts/verificar_permissoes.py http://127.0.0.1:8000   # local

O script pede o e-mail e a senha de duas contas (A e B); a senha é digitada
sem aparecer na tela. Com a conta A, cria uma viagem, uma atividade e um lugar
temporários (marcados com [TESTE-PERMISSOES]); com a conta B, tenta ler,
alterar e apagar esses dados. No fim, apaga tudo o que criou.

As contas não precisam ser amigas nem participar de viagens em comum.
Não use contas que compartilham viagens entre si: o teste espera que B seja
uma desconhecida para A.
"""

import getpass
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://rumo-backend-j0f6.onrender.com").rstrip("/")
MARK = "[TESTE-PERMISSOES]"


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{BASE}/api/{path}", data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Token {token}")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, None


def login(label):
    email = os.getenv(f"RUMO_EMAIL_{label}") or input(f"E-mail da conta {label}: ").strip()
    password = os.getenv(f"RUMO_SENHA_{label}") or getpass.getpass(f"Senha da conta {label}: ")
    status, data = call("POST", "auth/login/", body={"email": email, "password": password})
    if status != 200:
        sys.exit(f"Não foi possível entrar com a conta {label} ({status}).")
    return data["token"], data["user"]["id"]


def main():
    print(f"Backend: {BASE}")
    # O backend do Render pode estar "dormindo"; o primeiro pedido o acorda.
    call("GET", "health/")

    token_a, id_a = login("A")
    token_b, id_b = login("B")
    if id_a == id_b:
        sys.exit("As contas A e B precisam ser diferentes.")

    results = []

    def check(description, status, expected):
        ok = status in expected
        results.append(ok)
        print(f"  [{'OK' if ok else 'FALHOU'}] {description}: {status}")

    # --- Dados temporários da conta A -------------------------------------
    status, trip = call("POST", "trips/", token_a, {
        "title": f"{MARK} viagem",
        "origin": "São Paulo",
        "destination": "Lisboa, Portugal",
        "start_date": "2030-05-12",
        "end_date": "2030-05-13",
        "travelers_count": 1,
    })
    if status != 201:
        sys.exit(f"Não foi possível criar a viagem de teste ({status}): {trip}")
    trip_id = trip["id"]
    day_id = trip["days"][0]["id"]

    _, activity = call("POST", f"trips/{trip_id}/activities/", token_a, {
        "day": day_id, "title": f"{MARK} atividade",
    })
    activity_id = (activity or {}).get("id", 0)

    _, place = call("POST", "places/", token_a, {"name": f"{MARK} lugar"})
    place_id = place["id"]

    try:
        print("\nConta A acessa os próprios dados (esperado 200):")
        check("ver a viagem", call("GET", f"trips/{trip_id}/", token_a)[0], {200})
        check("ver o lugar", call("GET", f"places/{place_id}/", token_a)[0], {200})

        print("\nConta B tenta acessar os dados de A (esperado 403 ou 404):")
        denied = {403, 404}
        attempts = [
            ("ver a viagem", "GET", f"trips/{trip_id}/", None),
            ("editar a viagem", "PATCH", f"trips/{trip_id}/", {"title": "invadido"}),
            ("apagar a viagem", "DELETE", f"trips/{trip_id}/", None),
            ("duplicar a viagem", "POST", f"trips/{trip_id}/duplicate/", {}),
            ("gerar roteiro com IA", "POST", f"trips/{trip_id}/generate-itinerary/", {}),
            ("criar atividade", "POST", f"trips/{trip_id}/activities/", {"day": day_id, "title": "x"}),
            ("editar atividade", "PATCH", f"trips/{trip_id}/activities/{activity_id}/", {"title": "x"}),
            ("apagar atividade", "DELETE", f"trips/{trip_id}/activities/{activity_id}/", None),
            ("editar dia", "PATCH", f"trips/{trip_id}/days/{day_id}/", {"notes": "x"}),
            ("ver lugares da viagem", "GET", f"trips/{trip_id}/places/", None),
            ("adicionar o lugar de B à viagem", "POST", f"trips/{trip_id}/places/", {"place_ids": []}),
            ("ver membros", "GET", f"trips/{trip_id}/members/", None),
            ("convidar a si mesma", "POST", f"trips/{trip_id}/members/", {"user_id": id_b}),
            ("ver votações", "GET", f"trips/{trip_id}/polls/", None),
            ("ver questionário", "GET", f"trips/{trip_id}/questionnaire/me/", None),
            ("usar a calculadora de custos", "POST", f"trips/{trip_id}/cost-calculator/", {}),
            ("ver o lugar", "GET", f"places/{place_id}/", None),
            ("editar o lugar", "PATCH", f"places/{place_id}/", {"name": "invadido"}),
            ("apagar o lugar", "DELETE", f"places/{place_id}/", None),
        ]
        for description, method, path, body in attempts:
            check(description, call(method, path, token_b, body)[0], denied)

        print("\nListagens da conta B não mostram os dados de A:")
        _, trips_b = call("GET", "trips/", token_b)
        _, places_b = call("GET", "places/", token_b)
        trips_b = trips_b.get("results", trips_b) if isinstance(trips_b, dict) else trips_b or []
        places_b = places_b.get("results", places_b) if isinstance(places_b, dict) else places_b or []
        check("viagem fora da lista", 404 if all(t["id"] != trip_id for t in trips_b) else 200, {404})
        check("lugar fora da lista", 404 if all(p["id"] != place_id for p in places_b) else 200, {404})

        print("\nOs dados de A continuam intactos:")
        _, trip_now = call("GET", f"trips/{trip_id}/", token_a)
        check("título da viagem não mudou", 200 if trip_now and trip_now["title"] == f"{MARK} viagem" else 500, {200})
    finally:
        call("DELETE", f"places/{place_id}/", token_a)
        call("DELETE", f"trips/{trip_id}/", token_a)
        print("\nDados de teste apagados.")

    total, passed = len(results), sum(results)
    print(f"\nResultado: {passed} de {total} verificações passaram.")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
