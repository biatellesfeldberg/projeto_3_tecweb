# Validação do produto

Validação final do Rumo feita em 23/11/2026, depois da publicação no Render
(tarefas S2-06, S2-11, S2-12 e S2-21).

## 1. Testes automatizados

- Backend: `python manage.py test`, com **306 testes passando**. Eles cobrem
  autenticação, viagens, roteiro, lugares, colaboração, permissões, IA (com
  respostas simuladas) e o armazenamento das fotos no banco.
- Frontend: `npm run build` sem erros.

## 2. Fluxos no site publicado

| Fluxo | Resultado |
|---|---|
| Cadastro e login | ok |
| Perfil: preferências e foto (continua após recarregar) | ok |
| Planejar viagem | ok |
| Gerar roteiro com IA | ok, depois de ativar o faturamento do Gemini (veja abaixo) |
| Meus lugares e inclusão na viagem | ok |
| Recarregar páginas internas (`/viagens/1`, `/lugares`) | ok |
| Páginas protegidas sem login levam à tela de entrada | ok |

**Problema encontrado:** no plano gratuito do Gemini, a geração falhava com
"assistente indisponível". O log mostrava `503` (modelo sobrecarregado) em
quase todos os modelos e `404` nos modelos `2.5`, aposentados. O site tratou
o erro como esperado: mostrou a mensagem amigável e manteve o roteiro
anterior. A solução foi ativar o faturamento e usar o
`gemini-3.5-flash-lite`. Os detalhes estão em [deploy.md](deploy.md).

## 3. Responsividade e acessibilidade (S2-11)

Revisão das 16 telas no computador (1536 px) e no celular (375 px). Em cada
tela foram verificados:

- rolagem horizontal indevida;
- botões e links sem nome acessível;
- campos sem rótulo;
- imagens sem texto alternativo;
- presença de um `h1` e ordem dos títulos;
- contraste de texto (WCAG AA: 4,5:1);
- tamanho dos alvos de toque no celular.

Também foi testada a navegação por teclado.

O que já estava bom: `lang="pt-BR"`, título por página, link "Pular para o
conteúdo", foco visível em todos os elementos, foco levado ao conteúdo a
cada troca de página e diálogos nativos (`<dialog>`) que prendem e devolvem
o foco.

### Problemas encontrados e corrigidos (S2-12)

| Problema | Correção |
|---|---|
| `/ajuda` e `/conta/seguranca`, links do cabeçalho, abriam uma página em branco; endereços inexistentes também | Nova página de Ajuda, página "Página não encontrada" e remoção do link Segurança, que não tinha funcionalidade (não há troca de senha) |
| No celular, a aba ativa "Destino ideal" ficava escondida na rolagem lateral, com o texto quebrado | As abas passam a quebrar em linhas no celular e não quebram mais o texto |
| Cinza dos textos secundários com contraste 4,19:1 sobre o fundo verde-claro | Cor escurecida (`#65736f` → `#5c6a66`), com contraste ≥ 4,78:1 em todos os fundos |
| Sem login, o cabeçalho mostrava "Minhas viagens", "Meus lugares" e "Amigos", que só levavam de volta ao login | Links principais aparecem só para quem está logado |
| Link "Ajuda" com 20 px de altura no celular | Área de toque aumentada |

Também foram notadas duas faixas com rolagem lateral proposital (dias do
roteiro e abas da viagem), que funcionam bem com toque e teclado. As caixas
de seleção dos formulários ficam dentro dos rótulos, que também são
clicáveis.

## 4. Permissões no ambiente publicado (S2-06)

Sem login, foram feitos **164 pedidos** à API publicada (41 endpoints, com
GET, POST, PATCH e DELETE). Todos foram recusados (`401`, ou `405` para
método inexistente). Também foi verificado que:

- token falso é recusado;
- com `DEBUG=False`, erros não mostram detalhes internos;
- o `/admin` exige login;
- o CORS só libera o frontend publicado;
- há cabeçalhos de segurança (`X-Frame-Options: DENY`, `nosniff`);
- a chave do Gemini não aparece no código do frontend.

Entre contas, o script
[`scripts/verificar_permissoes.py`](../scripts/verificar_permissoes.py) usa
duas contas sem relação. A conta A cria uma viagem, uma atividade e um lugar
temporários, e a conta B tenta ver, editar, apagar, duplicar, gerar roteiro,
convidar a si mesma, usar a calculadora etc. No ambiente local:
**24 de 24 verificações passaram**, e os dados de teste foram apagados no fim.

| Ambiente | Resultado |
|---|---|
| Local | 24/24 |
| Publicado | não executado: o servidor roda o mesmo código testado localmente, e os testes sem login acima foram feitos no próprio site publicado. Para repetir: `python scripts/verificar_permissoes.py` |

## 5. Retorno de usuários

Teste rápido (10 a 15 minutos por pessoa) com pessoas de fora do grupo, no
site publicado e, se possível, no celular. A pessoa cria uma conta e tenta,
sem ajuda:

1. planejar uma viagem para um destino que gostaria de conhecer;
2. gerar o roteiro com IA e pedir um ajuste ("menos museus, mais
   gastronomia");
3. salvar um lugar em Meus lugares e levá-lo para a viagem;
4. ver o orçamento da viagem.

Perguntas depois do teste:

- De 1 a 5, quão fácil foi planejar a viagem?
- O roteiro gerado parece útil? O que você mudaria nele?
- Em que momento você ficou em dúvida sobre o que fazer?
- Você usaria o Rumo para planejar uma viagem com amigos? Por quê?

| Pessoa | Facilidade (1–5) | O que funcionou | Dificuldades | Sugestão |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Mudanças feitas a partir do retorno:** _preencher_.

## 6. Conferência dos requisitos da entrega (S2-24)

Conferido com o enunciado do Projeto 3 em 23/11/2026.

| Requisito | Situação |
|---|---|
| React no frontend e Django REST Framework no backend | ok |
| Cadastro e login | ok |
| Funcionalidade com IA generativa | ok (Gemini: roteiro, ajuste, destino ideal, calculadora) |
| Framework CSS | Tailwind CSS v4 instalado (reset e utilitários como `sr-only`); a maior parte do visual está em CSS próprio |
| Resultado público (deploy) e link no README | ok: https://rumo-frontend.onrender.com |
| Fluxo de telas no repositório | ok: `fluxo_de_telas.pdf` |
| Cronograma com entregas por sprint no README | ok (Sprint 1 e Sprint 2) |
| README com instruções para rodar o código | ok (backend, frontend, testes, dados de demonstração) |
| Quadro do GitHub (To Do, Doing, Done; responsável, tamanho P/M/G, datas de início e fim) | conferir no quadro antes das 09:30 de 24/11 |
| Commits significativos de todas as integrantes | ok: todas têm commits |
| Professora (`BarbaraTieko`) adicionada ao repositório | conferir em *Settings → Collaborators* |
| Exemplo de IA usada no desenvolvimento (apresentação) | depende da S2-17 |
| Diferencial com melhorias comprovadas (conceito A+) | avaliação da IA ([avaliacao-ia.md](avaliacao-ia.md)), testes e esta validação; falta o retorno de usuários (seção 5) |
| Questionário de trabalho em equipe da Sprint 2 | cada integrante responde |
