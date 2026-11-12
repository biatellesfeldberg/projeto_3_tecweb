# Contratos da API — Rumo

Este documento define como o frontend (React) e o backend (Django REST
Framework) conversam. Ele vale para **conta**, **viagens**, **geração de
roteiro** e **lugares salvos**.

- Endpoints marcados com ✅ já estão implementados.
- Endpoints marcados com 🛠️ ainda serão implementados, mas **devem seguir
  exatamente este contrato**. Enquanto isso, o frontend pode usar os dados
  simulados de `frontend/src/mocks/trips.js` (veja a seção
  [Desenvolvimento com dados simulados](#desenvolvimento-com-dados-simulados)).

Se for preciso mudar algum campo, atualize este arquivo **no mesmo commit** e
avise o grupo.

---

## Convenções gerais

| Item | Regra |
|---|---|
| URL base | `/api/` (em desenvolvimento, o Vite redireciona `/api` para `http://127.0.0.1:8000`) |
| Formato | JSON em requisições e respostas (exceto upload de foto, que usa `multipart/form-data`) |
| Nomes de campos | `snake_case`, em inglês (ex.: `start_date`, `travelers_count`) |
| Datas | `"AAAA-MM-DD"` (ex.: `"2027-05-12"`) |
| Horários | Resposta: `"HH:MM:SS"` (ex.: `"09:00:00"`). Requisição: aceita `"HH:MM"` ou `"HH:MM:SS"` |
| Data e hora | ISO 8601 com fuso (ex.: `"2026-11-12T08:30:00-03:00"`) |
| Valores em dinheiro e coordenadas | Chegam como **texto** (ex.: `"32000.00"`, `"38.711400"`) para não perder precisão. No frontend, use `Number(valor)` para fazer contas |
| Campos opcionais vazios | Texto vazio vira `""`. Números, datas e horários vazios viram `null` |
| Listas | Retornadas como array simples (sem paginação) |

### Autenticação

Depois do login ou cadastro, o backend devolve um `token`. Todas as rotas,
exceto cadastro, login e health check, exigem o cabeçalho:

```
Authorization: Token <token>
```

O frontend guarda o token em `sessionStorage` (`rumo.auth.token`), como já é
feito em `frontend/src/services/auth.js`.

### Formato dos erros

| Status | Quando | Corpo |
|---|---|---|
| `400` | Dados inválidos | Um objeto com o nome do campo e uma lista de mensagens: `{"end_date": ["A data de término deve ser igual ou posterior à data de início."]}`. Erros gerais vêm em `non_field_errors` |
| `401` | Sem token ou token inválido | `{"detail": "As credenciais de autenticação não foram fornecidas."}` ou `{"detail": "Token inválido."}` |
| `404` | Recurso não existe **ou pertence a outro usuário** | `{"detail": "Não encontrado."}` |
| `429` | Limite de uso da IA atingido | `{"detail": "Muitas solicitações ao assistente de viagens. Aguarde um pouco e tente novamente."}` |
| `502` | A IA respondeu em formato inválido | `{"detail": "O assistente de viagens devolveu uma resposta inválida. Tente novamente."}` |
| `503` | IA indisponível ou não configurada | `{"detail": "O assistente de viagens está indisponível no momento. Tente novamente em alguns instantes."}` |

As mensagens já vêm em português e podem ser exibidas diretamente para o
usuário.

> Por segurança, acessar a viagem de outra pessoa retorna `404`, e não `403`.
> Assim, o sistema não revela que a viagem existe.

---

## Opções (choices) compartilhadas

O **perfil** (`accounts.User`) e a **viagem** (`trips.Trip`) usam as mesmas
chaves. O frontend envia e recebe sempre a **chave**. O rótulo é só para
exibição.

### Estilo (`style`)

| Chave | Rótulo |
|---|---|
| `economic` | Econômico |
| `intermediate` | Intermediário |
| `comfort` | Conforto |

### Ritmo (`pace`)

| Chave | Rótulo |
|---|---|
| `relaxed` | Tranquilo |
| `moderate` | Moderado |
| `intense` | Intenso |

### Interesses (`interests`, uma lista de chaves)

| Chave | Rótulo |
|---|---|
| `beach` | Praia |
| `nature` | Natureza |
| `gastronomy` | Gastronomia |
| `adventure` | Aventura |
| `culture` | Cultura |
| `shopping` | Compras |
| `nightlife` | Vida noturna |
| `sightseeing` | Paisagens |

### Alcance dos destinos (`destination_preference`, só no perfil)

| Chave | Rótulo |
|---|---|
| `any` | Sem preferência |
| `domestic` | Nacionais |
| `international` | Internacionais |

### Tipo de viagem (`mode`)

| Chave | Rótulo |
|---|---|
| `solo` | Por conta própria |
| `group` | Com amigos |

### Status da viagem (`status`)

| Chave | Rótulo | Aba em "Minhas viagens" |
|---|---|---|
| `planning` | Em planejamento | Em planejamento |
| `upcoming` | Próxima | Próximas |
| `completed` | Realizada | Realizadas |

### Transporte (`transport`)

| Chave | Rótulo |
|---|---|
| `plane` | Avião |
| `car` | Carro |
| `bus` | Ônibus |
| `train` | Trem |
| `other` | Outro |

### Categoria da atividade (`category`)

Inclui todas as chaves de interesses, mais algumas próprias do roteiro:

| Chave | Rótulo |
|---|---|
| `gastronomy` | Gastronomia |
| `culture` | Cultura |
| `nature` | Natureza |
| `beach` | Praia |
| `sightseeing` | Paisagem |
| `shopping` | Compras |
| `nightlife` | Vida noturna |
| `adventure` | Aventura |
| `transport` | Deslocamento |
| `lodging` | Hospedagem |
| `free_time` | Tempo livre |
| `other` | Outro |

### Tipo de custo (`cost_type`)

| Chave | Rótulo | Exibição sugerida |
|---|---|---|
| `per_person` | Por pessoa | `R$ 60 / pessoa` |
| `total` | Total do grupo | `R$ 240 no total` |

---

## Conta ✅

Base: `/api/auth/`

### `POST /api/auth/register/`: cadastro (sem token)

Requisição:

```json
{
  "first_name": "Bia",
  "last_name": "Feldberg",
  "email": "bia@exemplo.com",
  "password": "senha-forte-123",
  "password_confirm": "senha-forte-123"
}
```

`last_name` é opcional. O e-mail é salvo em minúsculas.

Resposta `201`:

```json
{
  "user": {
    "id": 1,
    "first_name": "Bia",
    "last_name": "Feldberg",
    "email": "bia@exemplo.com"
  },
  "token": "f027c92c2eaeb7470b475ae0008a2723b151e9c0"
}
```

Erros `400` possíveis: `{"email": ["Já existe uma conta com este e-mail."]}`,
`{"password_confirm": ["As senhas não coincidem."]}`,
`{"password": ["Esta senha é muito curta. Ela precisa conter pelo menos 8 caracteres.", "..."]}`.

### `POST /api/auth/login/`: login (sem token)

Requisição:

```json
{ "email": "bia@exemplo.com", "password": "senha-forte-123" }
```

Resposta `200`: mesmo formato do cadastro (`user` + `token`).

Erro `401`: `{"detail": "E-mail ou senha inválidos."}`

### `POST /api/auth/logout/`: sair

Sem corpo. Invalida o token atual.

Resposta `200`: `{"detail": "Logout realizado com sucesso."}`

### `GET /api/auth/me/`: perfil do usuário logado

Resposta `200`:

```json
{
  "id": 1,
  "first_name": "Bia",
  "last_name": "Feldberg",
  "email": "bia@exemplo.com",
  "bio": "",
  "home_city": "São Paulo, Brasil",
  "photo": null,
  "preferred_destinations": ["Portugal", "Brasil"],
  "interests": ["culture", "gastronomy"],
  "style": "intermediate",
  "pace": "relaxed",
  "destination_preference": "any"
}
```

`photo` é a URL completa da imagem ou `null`. `style` e `pace` podem vir como
`""` se o usuário ainda não preencheu.

### `PATCH /api/auth/me/`: atualizar perfil

Envie só os campos que mudaram. Campos aceitos: `first_name`, `last_name`,
`bio`, `home_city`, `preferred_destinations`, `interests`, `style`, `pace`,
`destination_preference`.

```json
{ "interests": ["culture", "gastronomy"], "style": "intermediate", "pace": "relaxed" }
```

Resposta `200`: o perfil completo atualizado (mesmo formato do `GET`).

Erros `400`: `{"style": ["\"barato\" não é uma escolha válida."]}`. Campos que não
podem ser alterados, como `email`, retornam
`{"email": ["Campo não permitido nesta atualização."]}`.

### `PATCH /api/auth/me/photo/`: enviar foto

`multipart/form-data` com o campo `photo` (JPEG, PNG ou WebP, até 5 MB).
Resposta `200`: perfil completo.

### `DELETE /api/auth/me/photo/`: remover foto

Resposta `200`: perfil completo, com `"photo": null`.

---

## Viagens 🛠️ (issue S1-14)

Base: `/api/trips/`. Cada usuário só vê e altera as **próprias** viagens.

### Objeto `Trip` (resumo, usado na listagem)

```json
{
  "id": 12,
  "title": "Lisboa com calma",
  "origin": "São Paulo, Brasil",
  "destination": "Lisboa, Portugal",
  "start_date": "2027-05-12",
  "end_date": "2027-05-18",
  "duration_days": 7,
  "travelers_count": 4,
  "budget": "32000.00",
  "currency": "BRL",
  "mode": "group",
  "status": "planning",
  "cover_image_url": "https://images.exemplo.com/lisboa.jpg",
  "created_at": "2026-11-10T14:20:00-03:00",
  "updated_at": "2026-11-12T09:05:00-03:00"
}
```

| Campo | Tipo | Obrigatório ao criar | Observação |
|---|---|---|---|
| `id` | número | (somente leitura) | |
| `title` | texto (até 120) | sim | |
| `description` | texto | não | Só no detalhe |
| `origin` | texto (até 120) | sim | "Cidade de origem" |
| `destination` | texto (até 120) | não | `""` = "Ainda não escolhi meu destino" |
| `start_date` / `end_date` | data | sim | `end_date` ≥ `start_date` |
| `duration_days` | número | (somente leitura) | Calculado: dias entre as datas, incluindo o primeiro e o último |
| `travelers_count` | número 1–50 | não (padrão `1`) | |
| `budget` | texto decimal ou `null` | não | Orçamento total |
| `currency` | texto (3) | não (padrão `"BRL"`) | |
| `mode` | choice | não (padrão `"solo"`) | |
| `status` | choice | não (padrão `"planning"`) | |
| `style`, `pace` | choice ou `""` | não | Só no detalhe. Se omitidos na criação, são copiados do perfil |
| `transport` | choice ou `""` | não | Só no detalhe |
| `interests` | lista de chaves | não | Só no detalhe. Se omitido na criação, é copiado do perfil |
| `cover_image_url` | URL ou `""` | não | |
| `created_at`, `updated_at` | data e hora | (somente leitura) | |

### Objeto `TripDetail` (detalhe)

O mesmo do resumo, mais `description`, `style`, `pace`, `transport`,
`interests` e `days`:

```json
{
  "id": 12,
  "title": "Lisboa com calma",
  "description": "7 dias para descobrir a cidade, sem pressa.",
  "origin": "São Paulo, Brasil",
  "destination": "Lisboa, Portugal",
  "start_date": "2027-05-12",
  "end_date": "2027-05-18",
  "duration_days": 7,
  "travelers_count": 4,
  "budget": "32000.00",
  "currency": "BRL",
  "mode": "group",
  "status": "planning",
  "style": "intermediate",
  "pace": "relaxed",
  "transport": "plane",
  "interests": ["gastronomy", "culture"],
  "cover_image_url": "https://images.exemplo.com/lisboa.jpg",
  "created_at": "2026-11-10T14:20:00-03:00",
  "updated_at": "2026-11-12T09:05:00-03:00",
  "days": [
    {
      "id": 101,
      "date": "2027-05-12",
      "day_number": 1,
      "title": "Baixa e Alfama",
      "notes": "",
      "activities": [
        {
          "id": 1001,
          "day": 101,
          "title": "Café e uma volta pela Baixa",
          "description": "Comece o dia com um pastel de nata e caminhe pela Rua Augusta.",
          "category": "gastronomy",
          "start_time": "09:00:00",
          "end_time": "10:30:00",
          "duration_minutes": 90,
          "location_name": "Baixa",
          "address": "Rua Augusta, Lisboa",
          "latitude": "38.710800",
          "longitude": "-9.137700",
          "estimated_cost": "60.00",
          "cost_type": "per_person",
          "total_cost": "240.00",
          "notes": "",
          "image_url": "",
          "order": 1
        }
      ]
    }
  ]
}
```

`days` vem em ordem de data, e `activities` vem em ordem de `order` e depois
`start_time`.

### `GET /api/trips/`: listar minhas viagens

Filtro opcional: `?status=planning`, `?status=upcoming` ou `?status=completed`.

Resposta `200`: lista de `Trip` (resumo), ordenada por `start_date`.

```json
[
  { "id": 12, "title": "Lisboa com calma", "...": "..." },
  { "id": 13, "title": "Fim de semana no Rio", "...": "..." }
]
```

Sem viagens, a resposta é `[]`. Nesse caso, o frontend mostra o estado vazio.

### `POST /api/trips/`: criar viagem (formulário "Planejar viagem")

Requisição:

```json
{
  "title": "Lisboa com calma",
  "origin": "São Paulo, Brasil",
  "destination": "Lisboa, Portugal",
  "start_date": "2027-05-12",
  "end_date": "2027-05-18",
  "travelers_count": 4,
  "budget": "32000.00",
  "mode": "group",
  "style": "intermediate",
  "pace": "relaxed",
  "transport": "plane",
  "interests": ["gastronomy", "culture"]
}
```

Resposta `201`: `TripDetail`. O backend **cria automaticamente um dia
(`days`) para cada data** entre `start_date` e `end_date`, todos ainda sem
atividades.

Erro `400` (exemplo):

```json
{ "end_date": ["A data de término deve ser igual ou posterior à data de início."] }
```

### `GET /api/trips/{id}/`: detalhe da viagem

Resposta `200`: `TripDetail`. Se a viagem não existir ou for de outra pessoa,
retorna `404`.

### `PATCH /api/trips/{id}/`: editar viagem

Envie só os campos que mudaram (os mesmos aceitos na criação).

Resposta `200`: `TripDetail`.

Se as datas mudarem, os dias são ajustados: datas novas ganham dias vazios, e
dias fora do novo período são **removidos junto com suas atividades**. Avise o
usuário antes de encurtar uma viagem.

### `DELETE /api/trips/{id}/`: excluir viagem

Resposta `204` (sem corpo). Os dias e as atividades da viagem também são
apagados.

---

## Dias e atividades 🛠️ (issue S1-14)

### `PATCH /api/trips/{trip_id}/days/{day_id}/`: editar o dia ("Notas do dia")

Campos aceitos: `title`, `notes`. A data e o número do dia não podem ser
editados.

```json
{ "notes": "Levar casaco para o fim da tarde." }
```

Resposta `200`: o dia, no mesmo formato do item de `days`, com `activities`.

### `POST /api/trips/{trip_id}/activities/`: adicionar atividade

Requisição (`day` e `title` são obrigatórios):

```json
{
  "day": 101,
  "title": "Miradouro e tempo livre",
  "category": "sightseeing",
  "start_time": "15:00",
  "duration_minutes": 60,
  "location_name": "Miradouro de Santa Luzia",
  "latitude": "38.711700",
  "longitude": "-9.130200",
  "estimated_cost": "0.00",
  "cost_type": "per_person"
}
```

Resposta `201`: a atividade criada (formato de `activities`). Se `order` não
for enviado, a atividade vai para o final do dia.

Erros `400`: `{"day": ["Este dia não pertence a esta viagem."]}`,
`{"end_time": ["O horário de término deve ser posterior ao de início."]}`.

### `PATCH /api/trips/{trip_id}/activities/{activity_id}/`: editar atividade

Envie só os campos alterados. Para **mover a atividade para outro dia**, envie
um novo `day`.

Resposta `200`: a atividade atualizada. `total_cost` é recalculado.

### `DELETE /api/trips/{trip_id}/activities/{activity_id}/`: remover atividade

Resposta `204`.

### `POST /api/trips/{trip_id}/days/{day_id}/reorder/`: reordenar atividades do dia

```json
{ "activity_ids": [1003, 1001, 1002] }
```

A lista precisa conter **todas** as atividades daquele dia. Resposta `200`: o
dia com as atividades na nova ordem.

---

## Geração de roteiro com IA 🛠️ (issue S1-16)

### `POST /api/trips/{id}/generate-itinerary/`: gerar ou refazer o roteiro

Usa o Gemini para preencher os dias da viagem com atividades, considerando o
destino, as datas, o orçamento, o número de viajantes, o estilo, o ritmo e os
interesses da viagem.

Requisição (todos os campos são opcionais):

```json
{
  "replace_existing": true,
  "extra_instructions": "Incluir um dia em Sintra."
}
```

| Campo | Padrão | Significado |
|---|---|---|
| `replace_existing` | `true` | `true`: apaga as atividades atuais e gera tudo de novo. `false`: só preenche os dias que estão vazios |
| `extra_instructions` | `""` | Pedido livre do usuário (até 500 caracteres), usado no "Ajustar roteiro" |

Resposta `200`: `TripDetail` com os dias preenchidos.

**A resposta pode demorar de 10 a 60 segundos.** O frontend deve mostrar um
estado de carregamento ("Montando seu roteiro…") e impedir cliques
repetidos no botão.

Erros:

| Status | Quando | Exemplo de corpo |
|---|---|---|
| `400` | A viagem não tem destino | `{"destination": ["Escolha um destino antes de gerar o roteiro."]}` |
| `404` | A viagem não existe ou é de outra pessoa | `{"detail": "Não encontrado."}` |
| `429` | A cota do Gemini acabou | `{"detail": "Muitas solicitações ao assistente de viagens. Aguarde um pouco e tente novamente."}` |
| `502` | A IA devolveu algo inválido | `{"detail": "O assistente de viagens devolveu uma resposta inválida. Tente novamente."}` |
| `503` | O Gemini está fora do ar ou não foi configurado | `{"detail": "O assistente de viagens está indisponível no momento. Tente novamente em alguns instantes."}` |

Se a geração falhar, **o roteiro anterior é mantido**, sem nenhuma alteração
parcial.

---

## Lugares salvos ✅ (issue S1-20)

Base: `/api/places/`. É a coleção "Meus lugares": uma lista de desejos do
usuário que existe independentemente das viagens. Um lugar pode ser vinculado
a uma ou mais viagens, e aparece na aba **Lugares** de cada uma. Cada usuário
só vê e altera os **próprios** lugares.

### Objeto `Place`

```json
{
  "id": 7,
  "name": "Um café em Alfama",
  "city": "Lisboa",
  "country": "Portugal",
  "category": "gastronomy",
  "description": "Café pequeno com vista para o Tejo.",
  "notes": "Indicação da Ana. Ir no fim da tarde.",
  "address": "Largo das Portas do Sol, Lisboa",
  "latitude": "38.712400",
  "longitude": "-9.130000",
  "image_url": "https://images.exemplo.com/alfama.jpg",
  "trips": [
    { "id": 12, "title": "Lisboa com calma" }
  ],
  "created_at": "2026-11-12T10:15:00-03:00",
  "updated_at": "2026-11-12T10:15:00-03:00"
}
```

| Campo | Tipo | Obrigatório ao criar | Observação |
|---|---|---|---|
| `id` | número | (somente leitura) | |
| `name` | texto (até 150) | sim | |
| `city` | texto (até 120) | não | Usado nos filtros por cidade |
| `country` | texto (até 120) | não | |
| `category` | choice | não (padrão `"other"`) | Mesmas chaves da [categoria da atividade](#categoria-da-atividade-category), para o lugar poder virar atividade no roteiro |
| `description` | texto | não | |
| `notes` | texto | não | Observações pessoais |
| `address` | texto (até 255) | não | |
| `latitude` / `longitude` | texto decimal ou `null` | não | **Vêm juntas ou as duas `null`**. Aceitam número ou texto; mais de 6 casas decimais são arredondadas. Latitude entre -90 e 90, longitude entre -180 e 180 |
| `image_url` | URL ou `""` | não | |
| `trips` | lista de `{id, title}` | (somente leitura) | Viagens às quais o lugar está vinculado, em ordem de data. Lista vazia = "Ainda sem viagem" |
| `trip_ids` | lista de ids | não (somente escrita) | Vincula o lugar a essas viagens. No `PATCH`, **substitui** os vínculos atuais (`[]` desvincula de todas) |
| `created_at`, `updated_at` | data e hora | (somente leitura) | |

### `GET /api/places/`: listar meus lugares

Resposta `200`: lista de `Place`, do mais recente para o mais antigo. Sem
lugares, a resposta é `[]`.

Filtros opcionais (podem ser combinados):

| Parâmetro | Exemplo | Efeito |
|---|---|---|
| `search` | `?search=lisboa` | Busca (sem diferenciar maiúsculas) em nome, cidade, país, endereço, descrição e observações |
| `category` | `?category=gastronomy` | Só a categoria indicada. Chave inválida retorna `400` |
| `city` | `?city=Lisboa` | Cidade exata (sem diferenciar maiúsculas) |
| `trip` | `?trip=12` | Só os lugares vinculados à viagem 12 |
| `trip` | `?trip=none` | Só os lugares sem nenhuma viagem |

### `POST /api/places/`: cadastrar lugar

Requisição (só `name` é obrigatório):

```json
{
  "name": "Palácio da Pena",
  "city": "Sintra",
  "country": "Portugal",
  "category": "culture",
  "notes": "Comprar ingresso antes.",
  "latitude": "38.787600",
  "longitude": "-9.390400",
  "trip_ids": [12]
}
```

Resposta `201`: o `Place` criado.

Erros `400`: `{"name": ["Este campo pode não estar em branco."]}`,
`{"latitude": ["Informe a latitude e a longitude juntas, ou deixe as duas vazias."]}`,
`{"trip_ids": ["Viagem não encontrada."]}` (viagem inexistente ou de outra
pessoa).

### `GET /api/places/{id}/`: detalhe do lugar

Resposta `200`: `Place`. Se o lugar não existir ou for de outra pessoa,
retorna `404`.

### `PATCH /api/places/{id}/`: editar lugar

Envie só os campos que mudaram (os mesmos aceitos no cadastro).

Resposta `200`: o `Place` atualizado.

### `DELETE /api/places/{id}/`: remover lugar

Resposta `204`. O lugar sai também de todas as viagens. As viagens e as
atividades do roteiro **não** são alteradas.

### Lugares de uma viagem (aba "Lugares")

#### `GET /api/trips/{trip_id}/places/`: listar lugares da viagem

Resposta `200`: lista de `Place`, na ordem em que foram adicionados à viagem.

#### `POST /api/trips/{trip_id}/places/`: adicionar lugares à viagem

Usado no botão "Adicionar à viagem" de Meus lugares, com vários lugares
selecionados de uma vez.

```json
{ "place_ids": [7, 9] }
```

Resposta `200`: a lista **completa** de lugares da viagem (mesmo formato do
`GET`). Lugares que já estavam na viagem são ignorados, sem erro.

Erros: `400` `{"place_ids": ["Lugar não encontrado."]}` (lugar inexistente ou
de outra pessoa; nesse caso nenhum lugar é adicionado) ou
`{"place_ids": ["Esta lista pode não estar vazia."]}`.

#### `DELETE /api/trips/{trip_id}/places/{place_id}/`: tirar lugar da viagem

Resposta `204`. O lugar continua em Meus lugares. Se o lugar não estiver na
viagem, retorna `404`.

Em todas as rotas de lugares da viagem, uma viagem inexistente ou de outra
pessoa retorna `404`.

---

## Outros

### `GET /api/health/` ✅: verificar se o backend está no ar (sem token)

```json
{ "status": "ok", "message": "Backend do projeto funcionando." }
```

---

## Desenvolvimento com dados simulados

Para o frontend não precisar esperar o backend, existem:

- `frontend/src/mocks/trips.js`: viagens de exemplo no formato deste
  contrato, com os mesmos dados do fluxo de telas ("Lisboa com calma", "Fim de
  semana no Rio" e "Férias em grupo").
- `frontend/src/services/trips.js`: funções prontas (`listTrips`,
  `getTrip`, `createTrip`, `updateTrip`, `deleteTrip`, `updateDay`,
  `createActivity`, `updateActivity`, `deleteActivity`, `reorderActivities`,
  `generateItinerary`). Elas devolvem os dados simulados ou chamam a API de
  verdade, dependendo da constante `USE_MOCKS`.

**Por enquanto, os dados simulados vêm ligados por padrão.** Nenhuma
requisição de viagens é feita: os dados ficam só na memória do navegador e
voltam ao original quando a página é recarregada.

Quando os endpoints de viagens (S1-14) estiverem prontos, o padrão de
`USE_MOCKS` em `services/trips.js` passa a ser `false`. As telas não precisam
mudar. Para testar a API de verdade antes disso, rode o frontend com:

```bash
VITE_USE_MOCKS=false npm run dev
```

Os erros seguem o mesmo padrão de `services/auth.js`: as funções lançam
`ApiError`, com `message`, `fields` (erros por campo) e `status`.

## Permissões dos dados pessoais

- Perfil e foto utilizam o usuário identificado pelo token.
- Lugares e viagens são restritos aos respectivos donos.
- O backend define a propriedade dos recursos.
- Recursos inexistentes ou pertencentes a outro usuário retornam 404.
- Campos de identificação e privilégios não podem ser alterados pelo
  endpoint de atualização do perfil.

### Consulta protegida da foto

`GET /api/auth/me/photo/` exige o cabeçalho
`Authorization: Token <token>` e retorna o arquivo da foto do usuário
autenticado.

Sem autenticação, retorna 401. Se o usuário não tiver foto, retorna 404.

O campo `photo` do perfil retorna a URL completa desse endpoint ou `null`.
O frontend deve buscar a imagem com autenticação e convertê-la em Blob
para exibição.

As fotos não são mais disponibilizadas diretamente por `/media/`.

### Implementação dos endpoints de viagens

Os endpoints da S1-14 deverão utilizar as funções de
`backend/trips/permissions.py` para recuperar viagens, dias e atividades
autorizados antes de consultar ou modificar seus dados.

Os testes de permissões HTTP deverão ser ampliados quando esses
endpoints forem implementados.
