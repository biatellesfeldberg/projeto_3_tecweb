# Roteiro da apresentação: 24/11/2026

Duração sugerida: **10 a 12 minutos** de apresentação mais perguntas. Cada
parte tem uma responsável sugerida; ajustem como preferirem.

## Antes de começar (no dia, 15 minutos antes)

- [ ] Abrir https://rumo-backend-j0f6.onrender.com/api/health/ para "acordar"
      o backend, que dorme depois de 15 minutos sem uso.
- [ ] Abrir https://rumo-frontend.onrender.com e entrar com a conta que vai
      apresentar.
- [ ] Deixar pronta uma viagem **com roteiro já gerado**, para o caso de o
      Gemini estar lento ou indisponível na hora.
- [ ] Deixar pronta uma viagem em grupo com convites e questionários
      respondidos. Pode ser com as contas reais do grupo ou com os dados de
      demonstração (`seed_collaboration_demo`).
- [ ] Abrir uma segunda aba, em janela anônima, com outra integrante logada,
      para mostrar a colaboração.
- [ ] Ter o README e o `fluxo_de_telas.pdf` abertos em abas.

## 1. O problema e a proposta (1 min)

- Planejar uma viagem, sobretudo em grupo, espalha ideias em conversas,
  planilhas e abas do navegador, e ninguém concorda com o destino.
- O **Rumo** reúne tudo: a IA monta e ajusta o roteiro, e o grupo decide
  junto para onde ir.
- Público: pessoas que viajam com amigos ou família e querem um plano
  pronto sem perder o controle dele.

## 2. Demonstração (6 a 7 min)

Seguir o fluxo de uma pessoa planejando uma viagem com amigos:

1. **Conta:** mostrar rapidamente o perfil com preferências de viagem. Elas
   alimentam a IA.
2. **Planejar viagem:** criar uma viagem e mostrar a opção "Ainda não
   escolhi meu destino".
3. **Grupo:** convidar uma amiga (aba Grupo). Na outra aba, ela aceita o
   convite e responde ao questionário.
4. **Destino ideal:** mostrar a recomendação da IA a partir das respostas
   do grupo e, na aba Grupo, a votação para decidir.
5. **Roteiro com IA:** gerar o roteiro e mostrar os dias, as atividades e o
   mapa com o trajeto do dia.
   - Se o Gemini demorar ou falhar, mostrar a mensagem de erro (o roteiro
     anterior continua salvo) e seguir com a viagem preparada.
6. **Ajustar roteiro com IA:** pedir algo como "troque os museus por
   gastronomia no segundo dia" e mostrar que a IA **propõe** e a pessoa
   aplica ou descarta.
7. **Meus lugares:** levar um lugar salvo para o roteiro.
8. **Orçamento:** planejado × estimado e a calculadora.
9. Mostrar o site **no celular** (ou com o navegador estreito).

## 3. Como a IA foi usada no produto (1 min)

- Quatro usos com finalidade clara: gerar roteiro, ajustar roteiro, destino
  ideal do grupo e calculadora de custos.
- Decisões do grupo:
  - a IA responde em JSON com esquema fixo, e o backend valida antes de
    salvar;
  - a IA **propõe** e a pessoa decide;
  - se a IA falhar, nada do que estava salvo é perdido;
  - a chave fica só no backend.
- Avaliação das respostas: [avaliacao-ia.md](avaliacao-ia.md).

## 4. IA usada no desenvolvimento (2 min, exigido pela rubrica)

Exemplo concreto da tarefa **S2-17** (documentação da Luana). Estrutura
pedida pela professora:

1. o que o grupo pretendia fazer;
2. como usou a IA;
3. o que precisou corrigir ou adaptar;
4. como verificou o resultado.

Exemplo extra, da publicação (S2-22), caso ajude:

1. **O que queríamos:** publicar o site no Render.
2. **Como usamos a IA:** um assistente de programação preparou o código para
   produção (PostgreSQL, WhiteNoise, CORS) e ajudou a investigar o erro da IA
   no site publicado.
3. **O que precisou ser corrigido:**
   - o disco gratuito do Render apaga as fotos de perfil, então guardamos as
     fotos no banco;
   - o modelo padrão do Gemini estava sobrecarregado (`503`) e os modelos
     `2.5` tinham sido aposentados (`404`).
4. **Como verificamos:**
   - testes automatizados (306 passando);
   - os logs do Render;
   - a reprodução do erro com a mesma chave no computador;
   - o script de permissões (S2-06).

## 5. Processo e qualidade (1 min)

- Quadro de tarefas no GitHub com responsáveis, tamanhos e datas, e
  cronograma das duas sprints no README.
- Fluxo de telas (`fluxo_de_telas.pdf`).
- Testes automatizados no backend.
- Revisão de responsividade e acessibilidade, e verificação de permissões no
  site publicado ([validacao.md](validacao.md)).
- Publicação no Render ([deploy.md](deploy.md)).

## Perguntas prováveis

- **"Por que a IA às vezes demora?"** A geração leva de 5 a 20 segundos, e o
  plano gratuito do Gemini ficou instável. Por isso há tratamento de erro e o
  roteiro anterior nunca é perdido.
- **"Uma pessoa consegue ver a viagem de outra?"** Não. A API responde 404
  para dados de outras contas, e isso foi verificado com o script de
  permissões no site publicado.
- **"Onde fica a chave do Gemini?"** Só nas variáveis de ambiente do
  backend. O frontend nunca a recebe.
