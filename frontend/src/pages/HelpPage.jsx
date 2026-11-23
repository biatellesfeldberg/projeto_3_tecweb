import { ButtonLink, Card, PageHeading } from "../components/ui";
import "./help.css";

const topics = [
  {
    title: "Planejar uma viagem",
    text: "Em Minhas viagens, clique em Planejar viagem e informe origem, destino, datas, número de viajantes e orçamento. Se ainda não sabe para onde ir, marque Ainda não escolhi meu destino: o grupo pode descobrir o destino ideal depois.",
  },
  {
    title: "Gerar o roteiro com IA",
    text: "Na aba Roteiro da viagem, peça para a IA montar os dias. Depois, use Ajustar roteiro com IA para pedir mudanças em linguagem natural, ou edite, reordene e adicione atividades você mesmo.",
  },
  {
    title: "Guardar lugares",
    text: "Em Meus lugares, salve restaurantes, museus e passeios que você quer conhecer. Selecione vários e leve todos para o roteiro de uma viagem; os que têm coordenadas aparecem no mapa.",
  },
  {
    title: "Controlar o orçamento",
    text: "A aba Orçamento compara o valor planejado com os custos estimados das atividades e traz uma calculadora com valores aproximados do destino.",
  },
  {
    title: "Viajar em grupo",
    text: "Na aba Grupo, convide amigos para a viagem. Cada pessoa responde ao questionário de preferências e o Rumo sugere o destino ideal para o grupo; as decisões podem ser votadas.",
  },
  {
    title: "Se a IA não responder",
    text: "A geração pode levar até um minuto. Se o serviço de IA estiver indisponível, uma mensagem aparece e nada do que já estava salvo é perdido. Tente novamente em alguns instantes.",
  },
];

export default function HelpPage() {
  return (
    <>
      <PageHeading
        eyebrow="Ajuda"
        title="Como usar o Rumo."
        description="Um resumo do que dá para fazer em cada parte do site."
        action={<ButtonLink to="/viagens">Ir para minhas viagens</ButtonLink>}
      />

      <div className="help-grid">
        {topics.map((topic) => (
          <Card key={topic.title} className="help-card">
            <h2>{topic.title}</h2>
            <p>{topic.text}</p>
          </Card>
        ))}
      </div>
    </>
  );
}
