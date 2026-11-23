# Publicação no Render

O Rumo é publicado no [Render](https://render.com), no plano gratuito, em três
partes:

| Parte | Tipo no Render | Nome |
|---|---|---|
| Banco de dados | PostgreSQL | `rumo-db` |
| Backend (Django REST Framework + Gunicorn) | Web Service (Python) | `rumo-backend` |
| Frontend (React + Vite) | Static Site | `rumo-frontend` |

Tudo está descrito no arquivo [`render.yaml`](../render.yaml) (um *Blueprint*):
o Render cria as três partes de uma vez a partir do repositório.

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
  `VITE_API_URL` (definido no build). O backend libera o frontend publicado
  por CORS (`DJANGO_CORS_ALLOWED_ORIGIN_REGEXES`).
- **Segurança:** `DEBUG=False`, chave secreta gerada pelo Render, cookies
  seguros e HTTPS reconhecido atrás do proxy do Render. A chave do Gemini
  fica só no backend.

## Passo a passo

### 1. Acesso ao repositório

O repositório pertence a `biatellesfeldberg`. A conta do Render precisa
conseguir ler esse repositório pelo GitHub:

- se a dona do repositório criar a conta do Render (entrando com o GitHub), é
  só autorizar o acesso quando o Render pedir;
- se outra integrante criar a conta, ao conectar o GitHub o Render instala um
  aplicativo no repositório, e a dona precisa aprovar esse pedido no GitHub.

### 2. Criar o Blueprint

1. No painel do Render: **New → Blueprint**.
2. Escolha o repositório `projeto_3_tecweb`, branch `main`.
3. O Render lê o `render.yaml` e mostra o banco e os dois serviços. Ele pede
   os valores marcados como secretos:
   - `GEMINI_API_KEY`: chave do [Google AI Studio](https://aistudio.google.com/apikey);
   - `VITE_API_URL`: por enquanto, `https://rumo-backend.onrender.com`
     (confirme no passo 3).
4. Clique em **Apply** e aguarde. O primeiro build leva alguns minutos.

### 3. Conferir o endereço do backend

Se o nome `rumo-backend` já existir no Render, o serviço recebe um sufixo
(ex.: `rumo-backend-ab12.onrender.com`).

1. Abra o serviço **rumo-backend** e copie o endereço exibido no topo.
2. Se for diferente do que foi informado, abra **rumo-frontend → Environment**,
   corrija `VITE_API_URL` (sem barra no final) e faça
   **Manual Deploy → Deploy latest commit**. O frontend precisa ser
   reconstruído porque o endereço é gravado no build.

O CORS já aceita o frontend com ou sem sufixo, então o backend não precisa
mudar.

### 4. Verificar

- `https://<backend>/api/health/` responde `{"status": "ok", ...}`.
- O endereço do **rumo-frontend** abre o site; cadastro, login e criação de
  viagem funcionam.
- Recarregar uma página interna (ex.: `/viagens`) também funciona.

### 5. Dados de demonstração e conta de administração (opcional)

O plano gratuito não tem terminal no servidor, mas dá para rodar os comandos
do Django no seu computador apontando para o banco publicado:

1. Em **rumo-db → Connect**, copie a **External Database URL**.
2. Na pasta `backend`, com o ambiente virtual ativo:

   ```powershell
   $env:DATABASE_URL = "<External Database URL>"
   python manage.py seed_collaboration_demo
   python manage.py createsuperuser
   Remove-Item Env:DATABASE_URL
   ```

   No Git Bash: `DATABASE_URL="<External Database URL>" python manage.py seed_collaboration_demo`.

> Atenção: enquanto `DATABASE_URL` estiver definida, os comandos alteram o
> banco **publicado**. Remova a variável ao terminar.

## Limitações do plano gratuito

- O backend "dorme" após 15 minutos sem acesso; a primeira requisição depois
  disso pode levar cerca de 1 minuto. Antes de uma demonstração, abra
  `/api/health/` para acordá-lo.
- O banco gratuito do Render expira 30 dias após a criação.
- Cada push na branch `main` gera um novo deploy automático.
