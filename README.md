## Membros:
Ana Carolina Martinez Ferreira
Beatriz Telles Feldberg
Luana Hughes Freitas
Renata Hemsi Leventhal

## Sobre o Projeto:





## Sprint 1 — 10/11 a 13/11/2026

- [x] [S1-01] Fluxo de telas e tasklist
- [x] [S1-02] Configurar o backend em Django REST Framework
- [x] [S1-03] Implementar cadastro e autenticação
- [x] [S1-04] Implementar perfil e preferências de viagem no backend
- [ ] [S1-05] Implementar e testar as permissões dos dados pessoais
- [ ] [S1-06] Conferir autenticação na primeira versão publicada
- [x] [S1-07] Configurar React e a navegação principal
- [x] [S1-08] Desenvolver as telas de cadastro e login
- [ ] [S1-09] Desenvolver a tela de perfil e preferências
- [ ] [S1-10] Desenvolver Minhas viagens e o formulário de planejamento
- [ ] [S1-11] Implementar estados de carregamento, vazio e erro
- [ ] [S1-12] Validar o fluxo de conta e criação de viagem
- [x] [S1-13] Modelar viagens, dias e atividades
- [ ] [S1-14] Implementar os endpoints de gerenciamento de viagens
- [x] [S1-15] Implementar o serviço de comunicação com Gemini
- [ ] [S1-16] Gerar e salvar roteiros personalizados
- [ ] [S1-17] Testar falhas e consistência da geração de roteiros
- [ ] [S1-18] Definir os contratos entre frontend e backend
- [x] [S1-19] Organizar repositório, quadro e cronograma inicial
- [ ] [S1-20] Implementar os endpoints de lugares salvos
- [ ] [S1-21] Desenvolver Meus lugares e a seleção para viagens
- [ ] [S1-22] Desenvolver o roteiro diário com edição e mapa
- [ ] [S1-23] Publicar a primeira versão da aplicação
- [ ] [S1-24] Registrar a entrega e encerrar a Sprint 1

## Sprint 2 — 16/11 a 19/11/2026

- [ ] [S2-01] Implementar amizades e solicitações no backend
- [ ] [S2-02] Implementar integrantes e convites de viagem
- [ ] [S2-03] Implementar e testar permissões colaborativas
- [ ] [S2-04] Implementar o questionário individual do grupo
- [ ] [S2-05] Preparar dados de demonstração colaborativa
- [ ] [S2-06] Conferir permissões no ambiente publicado
- [ ] [S2-07] Desenvolver a página Amigos
- [ ] [S2-08] Desenvolver a aba Grupo e as votações
- [ ] [S2-09] Desenvolver questionário e resultado do destino ideal
- [ ] [S2-10] Desenvolver o painel de ajuste do roteiro
- [ ] [S2-11] Revisar responsividade e acessibilidade da interface
- [ ] [S2-12] Corrigir problemas de usabilidade encontrados nos testes
- [ ] [S2-13] Implementar a recomendação de destino para o grupo
- [ ] [S2-14] Implementar a calculadora de custo e duração
- [ ] [S2-15] Implementar o replanejamento e a inclusão de sugestões
- [ ] [S2-16] Avaliar e melhorar as respostas do Gemini
- [ ] [S2-17] Documentar um exemplo de IA usada no desenvolvimento
- [ ] [S2-18] Preparar o roteiro da apresentação e da demonstração
- [ ] [S2-19] Implementar votações e decisões no backend
- [ ] [S2-20] Desenvolver a aba Orçamento e a calculadora
- [ ] [S2-21] Validar o produto completo e coletar retorno de usuários
- [ ] [S2-22] Atualizar e verificar o deploy final
- [ ] [S2-23] Finalizar a documentação do projeto
- [ ] [S2-24] Encerrar o quadro e conferir os requisitos da entrega

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