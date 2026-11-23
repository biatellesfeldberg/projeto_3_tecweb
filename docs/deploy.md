# Publicação no Render

O Rumo está publicado no [Render](https://render.com), no plano gratuito:

| Parte | Tipo no Render | Endereço |
|---|---|---|
| Frontend (React + Vite) | Static Site `rumo-frontend` | https://rumo-frontend.onrender.com |
| Backend (Django REST Framework + Gunicorn) | Web Service `rumo-backend` | https://rumo-backend-j0f6.onrender.com |
| Banco de dados | PostgreSQL `rumo-db` (Ohio) | acessível só pelo backend |

A publicação foi feita manualmente pelo painel do Render, com os passos
abaixo. O arquivo [`render.yaml`](../render.yaml) descreve a mesma
configuração e pode ser usado como *Blueprint* (**New → Blueprint**) para
recriar tudo de uma vez.

## Como o código foi preparado

- **Banco:** com a variável `DATABASE_URL`, o Django usa o PostgreSQL
  (`dj-database-url` + `psycopg`). Sem ela, continua no SQLite local.
- **Servidor:** `gunicorn` com timeout de 120 s, porque a geração de roteiros
  pela IA pode levar até um minuto. As migrações rodam a cada início.
- **Arquivos estáticos (admin):** servidos pelo `whitenoise` após o
  `collectstatic` do build.
- **Arquivos enviados (fotos de perfil):** no plano gratuito o disco do
  servidor é apagado a cada reinício, que acontece sempre que o serviço
  "dorme" após 15 minutos sem uso. Por isso, com
  `DJANGO_MEDIA_STORAGE=database`, as fotos ficam guardadas no PostgreSQL
  (tabela `core.StoredFile`, em `backend/core/storage.py`). Elas continuam
  sendo entregues pelo endpoint autenticado `GET /api/auth/me/photo/`.
- **Comunicação entre frontend e backend:** o frontend chama o endereço de
  `VITE_API_URL` (gravado no build). O backend libera o frontend publicado
  por CORS (`DJANGO_CORS_ALLOWED_ORIGIN_REGEXES`).
- **Segurança:** `DEBUG=False`, chave secreta própria, cookies seguros e
  HTTPS reconhecido atrás do proxy do Render. A chave do Gemini fica só nas
  variáveis de ambiente do backend.

## Passo a passo

### 1. Banco de dados

**New → Postgres**:

| Campo | Valor |
|---|---|
| Name | `rumo-db` |
| Database / User | `rumo` / `rumo` |
| Region | Ohio (a mesma do backend) |
| Plan | Free |

O Render permite **um banco gratuito ativo por conta**. Se a conta já tiver
um (de outro projeto), é preciso suspendê-lo ou usar outra conta.

Quando o banco estiver *Available*, copie a **Internal Database URL**
(seção *Connections*).

### 2. Backend

**New → Web Service**, com o repositório `projeto_3_tecweb` (pela lista ou
por **Public Git Repository**):

| Campo | Valor |
|---|---|
| Name | `rumo-backend` |
| Language | Python 3 |
| Branch | `main` |
| Region | Ohio |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --no-input` |
| Start Command | `python manage.py migrate --no-input && gunicorn config.wsgi:application --timeout 120` |
| Health Check Path | `/api/health/` |
| Instance Type | Free |

Variáveis de ambiente:

| Variável | Valor |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `DATABASE_URL` | Internal Database URL do `rumo-db` |
| `DJANGO_SECRET_KEY` | valor gerado (botão *Generate*) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_MEDIA_STORAGE` | `database` |
| `DJANGO_CORS_ALLOWED_ORIGIN_REGEXES` | `^https://rumo-frontend(-[a-z0-9]+)*\.onrender\.com$` |
| `GEMINI_API_KEY` | chave do Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |

O endereço do próprio backend entra em `ALLOWED_HOSTS` automaticamente
(variável `RENDER_EXTERNAL_HOSTNAME`, definida pelo Render).

### 3. Frontend

**New → Static Site**, com o mesmo repositório:

| Campo | Valor |
|---|---|
| Name | `rumo-frontend` |
| Branch | `main` |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

Variáveis de ambiente:

| Variável | Valor |
|---|---|
| `VITE_API_URL` | endereço do backend, sem barra no final (`https://rumo-backend-j0f6.onrender.com`) |
| `NODE_VERSION` | `22.12.0` |

Depois de criar, em **Redirects/Rewrites**, adicione a regra
`/*` → `/index.html` com a ação **Rewrite**. Sem ela, recarregar uma página
interna (ex.: `/viagens/1`) dá erro 404.

Se o endereço do backend mudar, corrija `VITE_API_URL` e faça
**Manual Deploy → Deploy latest commit** no frontend: o endereço é gravado
no build.

### 4. Verificação (23/11/2026)

- `/api/health/` responde `{"status": "ok", ...}`;
- arquivos do admin carregam (WhiteNoise);
- o CORS libera só o frontend publicado;
- cadastro, login, criação de viagem e geração de roteiro funcionam no site;
- a foto de perfil continua aparecendo depois de recarregar a página;
- recarregar páginas internas funciona (regra de Rewrite).

### 5. Dados de demonstração (opcional)

O plano gratuito não tem terminal no servidor, mas os comandos do Django
podem rodar no computador apontando para o banco publicado. Copie a
**External Database URL** do `rumo-db` e, na pasta `backend` (cmd):

```cmd
env\Scripts\activate
set DATABASE_URL=<External Database URL>
python manage.py seed_collaboration_demo
set DATABASE_URL=
```

> Atenção: enquanto `DATABASE_URL` estiver definida, os comandos alteram o
> banco **publicado**. A última linha remove a variável.

## Problemas encontrados

- **IA indisponível (`503`) no site publicado.** Os logs do backend mostravam
  `Gemini: falha temporária 503`. O mesmo erro acontecia localmente com a
  mesma chave: o Google respondia *"This model is currently experiencing high
  demand"* para quase todos os modelos do plano gratuito, e os modelos
  `gemini-2.5-*` respondiam `404` (não disponíveis para chaves novas).
  **Solução:** ativar o faturamento no projeto da chave (Google AI Studio,
  *Paid tier*) e usar `gemini-3.5-flash-lite`. Cada roteiro custa uma fração
  de centavo; vale definir um limite de gastos no projeto.
- **Limite de um banco gratuito por conta** no Render: resolvido suspendendo
  o banco de um projeto anterior.

## Limitações do plano gratuito

- O backend "dorme" após 15 minutos sem acesso; a primeira requisição depois
  disso pode levar cerca de 1 minuto. Antes de uma demonstração, abra
  `/api/health/` para acordá-lo.
- O banco gratuito do Render expira 30 dias após a criação.
- Novos commits na `main` só aparecem no site depois de um novo deploy
  (automático se o repositório estiver conectado pelo GitHub; senão,
  **Manual Deploy** em cada serviço).
