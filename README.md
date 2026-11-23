## Membros:
Ana Carolina Martinez Ferreira
Beatriz Telles Feldberg
Luana Hughes Freitas
Renata Hemsi Leventhal

## Sobre o Projeto:

Nosso projeto é um site que usa IA para a criação de roteiros de viagem personalizados. Utilizamos uma API do Gemini. O usuário pode selecionar destinos, datas e outros detalhes de viagem como o orçamento e salvar seus planos em sua própria conta. 

### Para quem é

Pessoas que viajam em grupo ou sozinhas e perdem tempo juntando ideias em
conversas, planilhas e abas do navegador. O Rumo reúne tudo num só lugar:
a IA monta e ajusta o roteiro, e o grupo decide junto para onde ir.

### Funcionalidades

- **Conta:** cadastro, login, perfil com foto e preferências de viagem.
- **Minhas viagens:** planejamento com origem, destino, datas, viajantes e
  orçamento; viagens em planejamento, próximas e realizadas.
- **Roteiro com IA:** o Gemini gera o roteiro dia a dia; a pessoa edita,
  reordena e adiciona atividades, vê o trajeto do dia no mapa e pode pedir
  ajustes em linguagem natural (a IA propõe as mudanças e a pessoa aplica ou
  descarta).
- **Meus lugares:** coleção de lugares para visitar, que podem ser levados
  para o roteiro de qualquer viagem.
- **Orçamento:** comparação entre o valor planejado e os custos estimados,
  com uma calculadora de custo e duração feita pela IA.
- **Viagem em grupo:** amigos, convites, questionário individual de
  preferências, recomendação do destino ideal para o grupo e votações.

### Onde a IA é usada

| Funcionalidade | O que a IA faz |
|---|---|
| Gerar roteiro | Monta os dias com atividades, horários, custos e sugestões de hospedagem |
| Ajustar roteiro | Interpreta o pedido da pessoa e propõe alterações no roteiro existente |
| Destino ideal | Cruza as respostas do grupo e sugere destinos compatíveis |
| Calculadora | Estima custos de hospedagem, alimentação e transporte no destino |

As chamadas ficam em `backend/core/gemini.py`; a chave nunca vai para o
frontend. A avaliação das respostas da IA está em
[docs/avaliacao-ia.md](docs/avaliacao-ia.md).

### Tecnologias

- **Frontend:** React 19, React Router, Vite, Tailwind CSS e Leaflet (mapa
  com OpenStreetMap).
- **Backend:** Django 5, Django REST Framework e autenticação por token.
- **IA:** Google Gemini (`google-genai`).
- **Publicação:** Render (site estático, Gunicorn e PostgreSQL).

### Documentação

- [Fluxo de telas](fluxo_de_telas.pdf)
- [Quadro de tarefas](https://github.com/biatellesfeldberg/projeto_3_tecweb/projects)
- [Contratos da API](docs/contratos-api.md)
- [Avaliação das respostas da IA](docs/avaliacao-ia.md)
- [Publicação no Render](docs/deploy.md)
- [Validação do produto](docs/validacao.md)
- [Roteiro da apresentação](docs/apresentacao.md)

## Acesse o Rumo

- **Site:** https://rumo-frontend.onrender.com
- **API (verificação):** https://rumo-backend-j0f6.onrender.com/api/health/

Publicado no Render (plano gratuito): o backend "dorme" após 15 minutos sem
uso, então o primeiro acesso pode levar cerca de 1 minuto. Como a publicação
foi feita está em [docs/deploy.md](docs/deploy.md).

## Sprint 1 — 10/11 a 13/11/2026

- [x] [S1-01] Fluxo de telas e tasklist
- [x] [S1-02] Configurar o backend em Django REST Framework
- [x] [S1-03] Implementar cadastro e autenticação
- [x] [S1-04] Implementar perfil e preferências de viagem no backend
- [x] [S1-05] Implementar e testar as permissões dos dados pessoais
- [x] [S1-06] Conferir autenticação na primeira versão publicada
- [x] [S1-07] Configurar React e a navegação principal
- [x] [S1-08] Desenvolver as telas de cadastro e login
- [x] [S1-09] Desenvolver a tela de perfil e preferências
- [x] [S1-10] Desenvolver Minhas viagens e o formulário de planejamento
- [x] [S1-11] Implementar estados de carregamento, vazio e erro
- [x] [S1-12] Validar o fluxo de conta e criação de viagem
- [x] [S1-13] Modelar viagens, dias e atividades
- [x] [S1-14] Implementar os endpoints de gerenciamento de viagens
- [x] [S1-15] Implementar o serviço de comunicação com Gemini
- [x] [S1-16] Gerar e salvar roteiros personalizados
- [ ] [S1-17] Testar falhas e consistência da geração de roteiros
- [x] [S1-18] Definir os contratos entre frontend e backend
- [x] [S1-19] Organizar repositório, quadro e cronograma inicial
- [x] [S1-20] Implementar os endpoints de lugares salvos
- [x] [S1-21] Desenvolver Meus lugares e a seleção para viagens
- [x] [S1-22] Desenvolver o roteiro diário com edição e mapa
- [ ] [S1-23] Publicar a primeira versão da aplicação — *substituída pela publicação final (S2-22), por decisão do grupo*
- [x] [S1-24] Registrar a entrega e encerrar a Sprint 1

## Sprint 2 — 16/11 a 19/11/2026

- [x] [S2-01] Implementar amizades e solicitações no backend
- [x] [S2-02] Implementar integrantes e convites de viagem
- [x] [S2-03] Implementar e testar permissões colaborativas
- [x] [S2-04] Implementar o questionário individual do grupo
- [x] [S2-05] Preparar dados de demonstração colaborativa
- [ ] [S2-06] Conferir permissões no ambiente publicado
- [x] [S2-07] Desenvolver a página Amigos
- [x] [S2-08] Desenvolver a aba Grupo e as votações
- [x] [S2-09] Desenvolver questionário e resultado do destino ideal
- [x] [S2-10] Desenvolver o painel de ajuste do roteiro
- [x] [S2-11] Revisar responsividade e acessibilidade da interface
- [x] [S2-12] Corrigir problemas de usabilidade encontrados nos testes
- [x] [S2-13] Implementar a recomendação de destino para o grupo
- [x] [S2-14] Implementar a calculadora de custo e duração
- [x] [S2-15] Implementar o replanejamento e a inclusão de sugestões
- [x] [S2-16] Avaliar e melhorar as respostas da IA
- [ ] [S2-17] Documentar um exemplo de IA usada no desenvolvimento
- [ ] [S2-18] Preparar o roteiro da apresentação e da demonstração
- [x] [S2-19] Implementar votações e decisões no backend
- [x] [S2-20] Desenvolver a aba Orçamento e a calculadora
- [ ] [S2-21] Validar o produto completo e coletar retorno de usuários
- [x] [S2-22] Atualizar e verificar o deploy final
- [ ] [S2-23] Finalizar a documentação do projeto
- [ ] [S2-24] Encerrar o quadro e conferir os requisitos da entrega

## Contratos da API

Os endpoints, campos e exemplos de resposta de **conta**, **viagens**,
**geração de roteiro** e **lugares salvos** estão documentados em
[`docs/contratos-api.md`](docs/contratos-api.md). Qualquer mudança na API deve
atualizar esse arquivo no mesmo commit.

O frontend sempre usa a API real. Para trabalhar só na interface, sem o
backend, dá para ligar dados simulados (`frontend/src/mocks/trips.js`) com
`VITE_USE_MOCKS=true` no arquivo `frontend/.env.local`.

## Executar o backend localmente

Na primeira execução:

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
```

No Windows, ative o ambiente com:

```powershell
.venv\Scripts\activate
```

Copie `.env.example` para `.env` e configure uma chave própria em
`DJANGO_SECRET_KEY`. Para gerar a chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Configurar o Gemini

O backend usa o Google Gemini para gerar os roteiros e sugerir destinos. As
chamadas ficam centralizadas em `backend/core/gemini.py` e a chave nunca vai
para o frontend.

Para criar a chave:

1. Acesse https://aistudio.google.com/apikey e entre com uma conta Google.
2. Aceite os termos de uso, se for o primeiro acesso.
3. Clique em **Create API key**. Se for pedido um projeto, escolha
   **Create API key in new project**.
4. Copie a chave gerada (ela começa com `AIza`).

Depois, no arquivo `backend/.env`, preencha a linha `GEMINI_API_KEY` com a
sua chave, sem aspas e sem espaços:

```
GEMINI_API_KEY=AIza...
```

Opcionalmente, altere `GEMINI_MODEL` (padrão: `gemini-3.5-flash-lite`). Se o
servidor já estiver rodando, reinicie-o para que ele leia o `.env` de novo.

> **Plano gratuito do Gemini:** em 23/11/2026, os modelos `gemini-2.5-*`
> respondiam `404` (não estão mais disponíveis para chaves novas) e os demais
> modelos gratuitos respondiam `503` ("high demand") na maior parte das
> tentativas. Com o faturamento ativado no projeto do Google AI Studio
> (*Paid tier*), as gerações passaram a funcionar em poucos segundos; cada
> roteiro custa uma fração de centavo com o `gemini-3.5-flash-lite`.

> **Cuidado:** a chave é pessoal. Ela fica só no `.env`, que não vai para o
> GitHub. Não coloque a chave no `.env.example`, no código ou em mensagens.
> Se ela vazar, apague-a na mesma página do AI Studio e crie outra.

Sem a chave, o restante do backend funciona normalmente, mas as
funcionalidades de IA respondem com erro 503 informando que o assistente
não está configurado.

Para conferir se a chave está funcionando:

```bash
python manage.py shell -c "from core.gemini import generate_text; print(generate_text('Sugira um passeio em Lisboa em uma frase.'))"
```

Depois, execute:

```bash
python manage.py migrate
python manage.py runserver
```

API: http://127.0.0.1:8000/api/health/

Para criar uma conta administrativa:

```bash
python manage.py createsuperuser
```

### Dados de demonstração

Para ter contas, amizades, convites, questionários e votações prontos:

```bash
python manage.py seed_collaboration_demo
```

O comando mostra as contas criadas (`ana.demo@example.com`,
`bia.demo@example.com` etc.) e a senha delas. Os registros ficam marcados com
`[S2-05-DEMO]`.

## Executar o frontend localmente

Com o backend rodando em `http://127.0.0.1:8000`, em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Site: http://localhost:5173. O Vite encaminha as chamadas `/api` para o
backend local, então não é preciso configurar nada. Na publicação, o endereço
do backend vem de `VITE_API_URL` (veja [docs/deploy.md](docs/deploy.md)).

## Executar os testes

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python manage.py test
```

Os testes do Gemini usam respostas simuladas e não consomem a cota da API.

### Verificar as permissões no site publicado

O script [`scripts/verificar_permissoes.py`](scripts/verificar_permissoes.py)
entra com duas contas (A e B), cria dados temporários com a conta A e
confere que a conta B não consegue ler, alterar nem apagar esses dados.
No fim, apaga o que criou.

```bash
python scripts/verificar_permissoes.py                        # site publicado
python scripts/verificar_permissoes.py http://127.0.0.1:8000  # local
```
